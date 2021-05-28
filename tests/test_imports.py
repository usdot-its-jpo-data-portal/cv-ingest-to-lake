import json
import os
from unittest import TestCase, mock


TEST_ENV_VAR = {
    "TARGET_BUCKET": "",
    "SOURCE_KEY_PREFIX": "",
    "VALIDATION_QUEUE_NAME": ""
}

TEST_SOCRATA_ENV_VAR = {
    "SOCRATA_DATASET_ID": "xxxx-xxxx",
    "SOCRATA_PARAMS": json.dumps({"username": "someuser", "password": "somepassword", "app_token": "", "domain": "data.transportation.gov"})
}

class TestImports(TestCase):
    @mock.patch.dict(os.environ, TEST_ENV_VAR)
    def test_import_lambda__ingest_to_lake(self):
        import lambda__ingest_to_lake

    @mock.patch.dict(os.environ, TEST_SOCRATA_ENV_VAR)
    def test_import_lambda__lake_to_socrata(self):
        import lambda__lake_to_socrata