"""
Move file from ingest s3 bucket to ITS DataHub sandbox s3.

"""

from __future__ import print_function

import json
import logging
import os
from time import time
import traceback

from sandbox_exporter.s3 import CvPilotFileMover


logger = logging.getLogger()
logger.setLevel(logging.INFO)  # necessary to make sure aws is logging

TARGET_BUCKET = os.environ.get('TARGET_BUCKET')
SOURCE_BUCKET_PREFIX = 'usdot-its-datahub-'
SOURCE_KEY_PREFIX = os.environ.get('SOURCE_KEY_PREFIX', "")
ECS_TASK_JSON = json.loads(os.environ.get('ECS_TASK_JSON', '{}'))
VALIDATION_QUEUE_NAME = os.environ.get('VALIDATION_QUEUE_NAME', None)
if VALIDATION_QUEUE_NAME:
    VALIDATION_QUEUE_NAME = [i.strip() for i in VALIDATION_QUEUE_NAME.split(',')]


def lambda_handler(event, context):
    run(event)

def run(event, in_lambda=True):
    """AWS Lambda handler. """

    mover = CvPilotFileMover(target_bucket=TARGET_BUCKET,
                             source_bucket_prefix=SOURCE_BUCKET_PREFIX,
                             source_key_prefix=SOURCE_KEY_PREFIX,
                             validation_queue_names=VALIDATION_QUEUE_NAME)

    for bucket, key in mover.get_fps_from_event(event):
        if "nycdot" in bucket and in_lambda is True:
            ECS_TASK_JSON['overrides']['containerOverrides'] = [
                {
                    "name": ECS_TASK_JSON['taskDefinition'], 
                    "environment": [{"name": "EVENT", "value": json.dumps(event)}]
                }
            ]
            mover.session.client('ecs').run_task(**ECS_TASK_JSON)
            return
        try:
            mover.move_file(bucket, key)
        except Exception as e:
            # send_to_slack(traceback.format_exc())
            logger.error("Error while processing event record: {}".format(event))
            logger.error(traceback.format_exc())
            raise e

    logger.info('Processed events')


if __name__ == '__main__':
    # Section used by Fargate
    t0 = time()
    event = json.loads(os.environ.get('EVENT'))
    print('Starting event:')
    print(event)
    run(event, in_lambda=False)
    t1 = time()
    print(f'Run completed in {(t1-t0)/60:.02} minutes.')
    exit()
