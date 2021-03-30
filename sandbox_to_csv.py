"""
ITS DataHub Sandbox Exporter

Script for exporting ITS sandbox data from specified date range to merged CSV
or JSON files

optional arguments:
  -h, --help            show this help message and exit
  --bucket BUCKET       Name of the s3 bucket. Default: usdot-its-cvpilot-
                        public-data
  --pilot PILOT         Pilot name (options: wydot, thea). Default: wydot
  --message_type MESSAGE_TYPE
                        Message type (options: bsm, tim, spat). Default: tim
  --sdate SDATE         Starting generatedAt date of your data, in the format
                        of YYYY-MM-DD.
  --edate EDATE         Ending generatedAt date of your data, in the format of
                        YYYY-MM-DD. If not supplied, this will be set to 24
                        hours from the start date.
  --output_convention OUTPUT_CONVENTION
                        Supply string for naming convention of output file.
                        Variables available for use in this string include:
                        pilot, messate_type, sdate, edate. Note that a file
                        number will always be appended to the output file
                        name. Default: {pilot}_{message_type}_{sdate}_{edate}
  --json                Supply flag if file is to be exported as newline json
                        instead of CSV file. Default: False
  --aws_profile AWS_PROFILE
                        Supply name of AWS profile if not using default
                        profile. AWS profile must be configured in
                        ~/.aws/credentials on your machine. See https://boto3.
                        amazonaws.com/v1/documentation/api/latest/guide/config
                        uration.html#shared-credentials-file for more
                        information.
  --zip                 Supply flag if output files should be zipped together.
                        Default: False
  --log                 Supply flag if script progress should be logged and
                        not printed to the console. Default: False
"""
from __future__ import print_function
from argparse import ArgumentParser
import boto3
from botocore.exceptions import ProfileNotFound
from copy import copy
import dateutil.parser
from datetime import datetime, timedelta
from functools import reduce
import json
import logging
import os
import csv
import threading
import time
import traceback
import zipfile

from sandbox_exporter.flattener import load_flattener
from sandbox_exporter.s3 import S3Helper


class SandboxExporter(object):

    def __init__(self, bucket='usdot-its-cvpilot-public-data', pilot='wydot',
                message_type='bsm', sdate=None, edate=None, csv=True, zip=False, log=False,
                output_convention='{pilot}_{message_type}_{sdate}_{edate}',
                aws_profile="default"):
        # set up
        self.bucket = bucket
        self.pilot = pilot
        self.message_type = message_type
        self.sdate = None
        self.edate = None
        self.csv = csv
        self.zip = zip
        self.output_convention = output_convention
        self.aws_profile = aws_profile
        self.print_func = print
        if log:
            logging.basicConfig(filename='sandbox_to_csv.log', format='%(asctime)s %(message)s')
            logger = logging.getLogger()
            logger.setLevel(logging.INFO)
            self.print_func = logger.info

        if sdate:
            self.sdate = dateutil.parser.parse(sdate)
        if edate:
            self.edate = dateutil.parser.parse(edate)
        else:
            self.edate = self.sdate + timedelta(hours=24)

        self.s3_helper = S3Helper(aws_profile=aws_profile)

        flattener_mod = load_flattener('{}/{}'.format(pilot, message_type.upper()))
        self.flattener = flattener_mod()
        self.current_recs = []
        self.file_names = []

    def get_folder_prefix(self, dt):
        y,m,d,h = dt.strftime('%Y-%m-%d-%H').split('-')
        folder = '{}/{}/{}/{}/{}/{}'.format(self.pilot, self.message_type.upper(), y, m, d, h)
        return folder

    def write_json_newline(self, recs, fp):
        with open(fp, 'w') as outfile:
            for r in recs:
                outfile.write(json.dumps(r))
                outfile.write('\n')
        self.file_names.append(fp)

    def write_csv(self, recs, fp):
        flat_recs = []
        for r in recs:
            flat_recs += self.flattener.process_and_split(r)

        with open(fp, mode='w') as csv_file:
            field_names = reduce(lambda x, y: set(list(x)+list(y)), flat_recs)
            writer = csv.DictWriter(csv_file, fieldnames=field_names)
            writer.writeheader()
            for flat_rec in flat_recs:
                writer.writerow(flat_rec)
        self.file_names.append(fp)

    def write(self, recs, fp):
        if self.csv:
            ext = '.csv'
            self.write_csv(recs, fp+ext)
        else:
            ext = '.txt'
            self.write_json_newline(recs, fp+ext)
        self.print_func('Wrote {} recs to {}'.format(len(recs), fp+ext ))

    def zip_files(self, fp_params):
        outfp = (self.output_convention+'.zip').format(**fp_params)
        with zipfile.ZipFile(outfp, 'w') as outzip:
            for fp in self.file_names:
                outzip.write(fp, compress_type=zipfile.ZIP_DEFLATED)
                os.remove(fp)
        self.print_func('Output zip file containing {} files at:\n{}'.format(len(self.file_names), outfp))


    def process(self, key):
        sb,sk = key
        stream = self.s3_helper.get_data_stream(sb, sk)
        recs = []
        for r in self.s3_helper.newline_json_rec_generator(stream):
            if self.csv:
                recs += self.flattener.process_and_split(r)
            else:
                recs.append(r)
        self.current_recs += recs

    def run(self):
        self.print_func('===========START===========')
        self.print_func('Exporting {} {} data between {} and {}'.format(self.pilot, self.message_type, self.sdate, self.edate))
        t0 = time.time()
        fp_params = {
            'pilot': self.pilot,
            'message_type': self.message_type.lower(),
            'sdate': self.sdate.strftime('%Y%m%d%H'),
            'edate': self.edate.strftime('%Y%m%d%H')
        }
        fp = lambda filenum: (self.output_convention+'_{filenum}').format(filenum=filenum, **fp_params)
        sfolder = self.get_folder_prefix(self.sdate)
        efolder = self.get_folder_prefix(self.edate)

        numkeys = 0
        filenum = 0
        numrecs = 0
        curr_folder = sfolder
        curr_dt = copy(self.sdate)
        while curr_folder < efolder:
            keys = self.s3_helper.get_fps_from_prefix(self.bucket, curr_folder)
            if len(keys) > 0:
                self.print_func('Processing {} keys from {}'.format(len(keys), curr_folder))
            for key in keys:
                self.process(key)
            if len(keys) > 0:
                self.print_func('{} recs processed from {}'.format(len(self.current_recs), curr_folder))

            numkeys += len(keys)
            curr_dt += timedelta(hours=1)
            curr_folder = self.get_folder_prefix(curr_dt)

            if len(self.current_recs) > 10000:
                self.write(self.current_recs, fp(filenum))
                numrecs += len(self.current_recs)
                self.current_recs = []
                filenum += 1

        if self.current_recs:
            self.write(self.current_recs, fp(filenum))
            numrecs += len(self.current_recs)
            filenum += 1
        t1 = time.time()
        self.print_func('===========================')
        self.print_func('{} keys retrieved between s3://{}/{} and s3://{}/{}'.format(numkeys, self.bucket, sfolder, self.bucket, efolder ))
        self.print_func('{} records read and written to {} files in {} min'.format(numrecs, filenum, (t1-t0)/60))
        if self.zip and self.file_names:
            self.zip_files(fp_params)
        elif self.file_names:
            self.print_func('Output files:\n{}'.format('\n'.join(self.file_names)))
        self.print_func('============END============')


if __name__ == '__main__':
    """
    Sample Usage
    Retrieve all WYDOT TIM data from 2019-09-16:
    python -u sandbox_to_csv.py --pilot wydot --message_type tim --sdate 2019-09-16

    Retrieve all WYDOT TIM data between 2019-09-16 to 2019-09-18:
    python -u sandbox_to_csv.py --pilot thea --message_type tim --sdate 2019-09-16 --edate 2019-09-18

    Retrieve all WYDOT TIM data between 2019-09-16 to 2019-09-18 in json newline format (instead of flattened CSV):
    python -u sandbox_to_csv.py --pilot thea --message_type tim --sdate 2019-09-16 --edate 2019-09-18 --json
    """

    parser = ArgumentParser(description="Script for exporting ITS sandbox data from specified date range to merged CSV files")
    parser.add_argument('--bucket', default="test-usdot-its-cvpilot-public-data", help="Name of the s3 bucket. Default: usdot-its-cvpilot-public-data")
    parser.add_argument('--pilot', default="wydot", help="Pilot name (options: wydot, thea). Default: wydot")
    parser.add_argument('--message_type', default="tim", help="Message type (options: bsm, tim, spat). Default: tim")
    parser.add_argument('--sdate', default=None, required=True, help="Starting generatedAt date of your data, in the format of YYYY-MM-DD.")
    parser.add_argument('--edate', default=None, help="Ending generatedAt date of your data, in the format of YYYY-MM-DD. If not supplied, this will be set to 24 hours from the start date.")
    parser.add_argument('--output_convention', default='{pilot}_{message_type}_{sdate}_{edate}', help="Supply string for naming convention of output file. Variables available for use in this string include: pilot, messate_type, sdate, edate. Note that a file number will always be appended to the output file name. Default: {pilot}_{message_type}_{sdate}_{edate}")
    parser.add_argument('--json', default=False, action='store_true', help="Supply flag if file is to be exported as newline json instead of CSV file. Default: False")
    parser.add_argument('--aws_profile', default='default', help="Supply name of AWS profile if not using default profile. AWS profile must be configured in ~/.aws/credentials on your machine. See https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#shared-credentials-file for more information.")
    parser.add_argument('--zip', default=False, action='store_true', help="Supply flag if output files should be zipped together. Default: False")
    parser.add_argument('--log', default=False, action='store_true', help="Supply flag if script progress should be logged and not printed to the console. Default: False")
    args = parser.parse_args()

    exporter = SandboxExporter(
        bucket=args.bucket,
        pilot=args.pilot,
        message_type=args.message_type,
        sdate=args.sdate,
        edate=args.edate,
        output_convention=args.output_convention,
        csv=bool(not args.json),
        aws_profile=args.aws_profile,
        zip=args.zip,
        log=args.log)
    exporter.run()
