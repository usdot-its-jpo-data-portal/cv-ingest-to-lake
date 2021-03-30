"""
Move file from ingest s3 bucket to ITS DataHub sandbox s3.

"""

from __future__ import print_function

import logging
import boto3
from datetime import datetime
from gzip import GzipFile
from io import TextIOWrapper
import json
import os
import re
import requests
import traceback
import uuid

from sandbox_exporter.s3 import S3Helper

logger = logging.getLogger()
logger.setLevel(logging.INFO)  # necessary to make sure aws is logging


class CvPilotFileMover(S3Helper):

    def __init__(self, source_bucket_prefix='usdot-its-datahub-', source_key_prefix=None, validation_queue_names=[], *args, **kwargs):
        super(CvPilotFileMover, self).__init__(*args, **kwargs)
        self.source_bucket_prefix = source_bucket_prefix
        self.source_key_prefix = source_key_prefix or ''
        self.queues = []
        self.pilot_name = None
        self.message_type = None

        if validation_queue_names:
            for validation_queue_name in validation_queue_names:
                sqs = boto3.resource('sqs')
                queue = sqs.get_queue_by_name(QueueName=validation_queue_name)
                self.queues.append(queue)

    def generate_outfp(self, ymdh_data_dict, source_bucket, source_key):
        if not ymdh_data_dict:
            self.print_func('File is empty: s3://{}/{}'.format(source_bucket, source_key))
            return None

        original_ymdh = "-".join(source_key.split('/')[-5:-1])
        no_change = "".join(ymdh_data_dict.keys()) == original_ymdh

        filename_prefix = self.target_bucket.replace('-public-data', '')
        regex_str = r'(?:test-)?{}(.*)-ingest'.format(self.source_bucket_prefix)
        regex_finds = re.findall(regex_str, source_bucket)
        if len(regex_finds) == 0:
            # if source bucket is sandbox
            pilot_name = source_key.split('/')[0]
            message_type = source_key.split('/')[1]
            stream_version = '0'
            if no_change and source_bucket == self.target_bucket:
                self.print_func('No need to reorder data at s3://{}/{}'.format(source_bucket, source_key))
                return None
        else:
            pilot_name = regex_finds[0].lower()
            message_type = source_key.strip(self.source_key_prefix).split('/')[0]

            # get stream version
            regex_str2 = filename_prefix+r'-(?:.*)-public-(\d)-(?:.*)'
            stream_version_res = re.findall(regex_str2, source_key)
            if not stream_version_res:
                stream_version = '0'
            else:
                stream_version = stream_version_res[0]

        def outfp_func(ymdh):
            y,m,d,h = ymdh.split('-')
            ymdhms = '{}-00-00'.format(ymdh)
            uuid4 = str(uuid.uuid4())

            target_filename = '-'.join([filename_prefix, message_type.lower(), 'public', str(stream_version), ymdhms, uuid4])
            target_prefix = os.path.join(pilot_name, message_type, y, m, d, h)
            target_key = os.path.join(target_prefix, target_filename)
            return target_key

        self.pilot_name  = pilot_name
        self.message_type = message_type

        return outfp_func

    def get_ymdh(self, rec):
        recordGeneratedAt = rec['metadata'].get('recordGeneratedAt')
        if not recordGeneratedAt:
            recordGeneratedAt = rec['payload']['data']['timeStamp']
        try:
            dt = datetime.strptime(recordGeneratedAt[:14].replace('T', ' '), '%Y-%m-%d %H:')
        except:
            self.print_func(traceback.format_exc())
            recordReceivedAt = rec['metadata'].get('odeReceivedAt')
            dt = datetime.strptime(recordReceivedAt[:14].replace('T', ' '), '%Y-%m-%d %H:')
            self.print_func('Unable to parse {} timestamp. Using odeReceivedAt timestamp of {}'.format(recordGeneratedAt, recordReceivedAt))
        recordGeneratedAt_ymdh = datetime.strftime(dt, '%Y-%m-%d-%H')
        return recordGeneratedAt_ymdh


    def move_file(self, source_bucket, source_key):
        # read triggering file
        source_path = os.path.join(source_bucket, source_key)
        self.print_func('Triggered by file: {}'.format(source_path))

        # sort all files by generatedAt timestamp ymdh
        ymdh_data_dict = {}
        data_stream = self.get_data_stream(source_bucket, source_key)
        for rec in self.newline_json_rec_generator(data_stream):
            recordGeneratedAt_ymdh = self.get_ymdh(rec)
            if recordGeneratedAt_ymdh not in ymdh_data_dict:
                ymdh_data_dict[recordGeneratedAt_ymdh] = []
            ymdh_data_dict[recordGeneratedAt_ymdh].append(rec)

        # generate output path
        outfp_func = self.generate_outfp(ymdh_data_dict, source_bucket, source_key)
        if outfp_func is None:
            return

        for ymdh, recs in ymdh_data_dict.items():
            target_key = outfp_func(ymdh)
            target_path = os.path.join(self.target_bucket, target_key)

            # copy data
            self.print_func('Writing {} records from \n{} -> \n{}'.format(len(recs), source_path, target_path))
            self.write_recs(recs, self.target_bucket, target_key)
            self.print_func('File written')
            if self.queues:
                for queue in self.queues:
                    msg = {
                    'bucket': self.target_bucket,
                    'key': target_key,
                    'pilot_name': self.pilot_name,
                    'message_type': self.message_type.lower()
                    }
                    queue.send_message(MessageBody=json.dumps(msg))

        if len(self.err_lines) > 0:
            self.print_func('{} lines not read in file. Keep file at: {}'.format(len(self.err_lines), source_path))
        else:
            self.print_func('Delete file: {}'.format(source_path))
            self.delete_file(source_bucket, source_key)
        return
