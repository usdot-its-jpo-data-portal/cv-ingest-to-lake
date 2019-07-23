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


logger = logging.getLogger()
logger.setLevel(logging.INFO)  # necessary to make sure aws is logging


class S3FileMover(object):

    def __init__(self, target_bucket, log=True):
        self.target_bucket = target_bucket
        self.s3_client = boto3.client('s3')
        self.print_func = print
        if log:
            self.print_func = logger.info
        self.err_lines = []

    def get_fps_from_event(self, event):
        bucket_key_tuples = [(e['s3']['bucket']['name'], e['s3']['object']['key']) for e in event['Records']]
        bucket_key_dict = {os.path.join(bucket, key): (bucket, key) for bucket, key in bucket_key_tuples}
        bucket_key_tuples_deduped = list(bucket_key_dict.values())
        return bucket_key_tuples_deduped

    def get_data_stream(self, bucket, key):
        obj = self.s3_client.get_object(Bucket=bucket, Key=key)
        if key[-3:] == '.gz':
            gzipped = GzipFile(None, 'rb', fileobj=obj['Body'])
            data = TextIOWrapper(gzipped)
        else:
            data = obj['Body']._raw_stream
        return data

    def newline_json_rec_generator(self, data_stream):
        line = data_stream.readline()
        while line:
            if type(line) == bytes:
                line_stripped = line.strip(b'\n')
            else:
                line_stripped = line.strip('\n')

            try:
                if line_stripped:
                    yield json.loads(line_stripped)
            except:
                self.print_func(traceback.format_exc())
                self.print_func('Invalid json line. Skipping: {}'.format(line))
                self.err_lines.append(line)
            line = data_stream.readline()


    def write_recs(self, recs, bucket, key):
        outbytes = "\n".join([json.dumps(i) for i in recs if i]).encode('utf-8')
        self.s3_client.put_object(Bucket=bucket, Key=key, Body=outbytes)

    def delete_file(self, bucket, key):
        self.s3_client.delete_object(Bucket=bucket, Key=key)

    def move_file(self, source_bucket, source_key):
        source_path = os.path.join(source_bucket, source_key)
        self.print_func('Triggered by file: {}'.format(source_path))

        data_stream = self.get_data_stream(source_bucket, source_key)
        recs = []
        for rec in self.newline_json_rec_generator(data_stream):
            recs.append(rec)

        if recs:
            target_key = source_key
            target_path = os.path.join(self.target_bucket, target_key)
            self.print_func('Writing {} records from {} -> {}'.format(len(recs), source_path, target_path))
            self.write_recs(recs, self.target_bucket, target_key)
        else:
            self.print_func('File is empty: {}'.format(source_path))

        self.print_func('Delete file: {}'.format(source_path))
        self.delete_file(source_bucket, source_key)


class CvPilotFileMover(S3FileMover):

    def __init__(self, source_bucket_prefix='usdot-its-datahub-', source_key_prefix=None, validation_queue_name=None, *args, **kwargs):
        super(CvPilotFileMover, self).__init__(*args, **kwargs)
        self.source_bucket_prefix = source_bucket_prefix
        self.source_key_prefix = source_key_prefix or ''
        self.queue = None

        if validation_queue_name:
            sqs = boto3.resource('sqs')
            self.queue = sqs.get_queue_by_name(QueueName=validation_queue_name)

    def move_file(self, source_bucket, source_key):
        # read triggering file
        source_path = os.path.join(source_bucket, source_key)
        self.print_func('Triggered by file: {}'.format(source_path))

        # sort all files by generatedAt timestamp ymdh
        ymdh_data_dict = {}
        data_stream = self.get_data_stream(source_bucket, source_key)
        for rec in self.newline_json_rec_generator(data_stream):
            recordGeneratedAt = rec['metadata']['recordGeneratedAt']
            recordGeneratedAt_dt = datetime.strptime(recordGeneratedAt[:19].replace('T', ' '), '%Y-%m-%d %H:%M:%S')
            recordGeneratedAt_ymdh = datetime.strftime(recordGeneratedAt_dt, '%Y-%m-%d-%H')
            if recordGeneratedAt_ymdh not in ymdh_data_dict:
                ymdh_data_dict[recordGeneratedAt_ymdh] = []
            ymdh_data_dict[recordGeneratedAt_ymdh].append(rec)

        # TODO: add validator

        if ymdh_data_dict:
            # generate outpath variables
            regex_str = r'(?:test-)?{}(.*)-ingest'.format(self.source_bucket_prefix)
            pilot_name = re.findall(regex_str, source_bucket)[0].lower()
            message_type = source_key.strip(self.source_key_prefix).split('/')[0]
            filename_prefix = self.target_bucket.replace('-public-data', '')

            # get stream version
            regex_str2 = filename_prefix+r'-(?:.*)-public-(\d)-(?:.*)'
            stream_version_res = re.findall(regex_str2, source_key)
            if not stream_version_res:
                stream_version = '0'
            else:
                stream_version = stream_version_res[0]

            for ymdh, recs in ymdh_data_dict.items():
                y,m,d,h = ymdh.split('-')
                ymdhms = '{}-00-00'.format(ymdh)
                uuid4 = str(uuid.uuid4())

                target_filename = '-'.join([filename_prefix, message_type.lower(), 'public', str(stream_version), ymdhms, uuid4])
                target_prefix = os.path.join(pilot_name, message_type, y, m, d, h)
                target_key = os.path.join(target_prefix, target_filename)
                target_path = os.path.join(self.target_bucket, target_key)

                # copy data
                self.print_func('Writing {} records from \n{} -> \n{}'.format(len(recs), source_path, target_path))
                self.write_recs(recs, self.target_bucket, target_key)
                self.print_func('File written')
                if self.queue and pilot_name == 'wydot':
                    msg = {
                    'bucket': self.target_bucket,
                    'key': target_key,
                    'pilot_name': pilot_name,
                    'message_type': message_type.lower()
                    }
                    self.queue.send_message(
                        MessageBody=json.dumps(msg),
                        MessageGroupId=str(uuid.uuid4())
                    )
        else:
            self.print_func('File is empty: {}'.format(source_path))

        if len(self.err_lines) > 0:
            self.print_func('{} lines not read in file. Keep file at: {}'.format(len(self.err_lines), source_path))
        else:
            self.print_func('Delete file: {}'.format(source_path))
            self.delete_file(source_bucket, source_key)
        return