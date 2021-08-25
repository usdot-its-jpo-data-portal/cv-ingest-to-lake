import json
import os
from unittest import TestCase, mock


TEST_ENV_VAR = {
    "TARGET_BUCKET": "test-usdot-its-cvpilot-public-data",
    "SOURCE_KEY_PREFIX": "",
    "VALIDATION_QUEUE_NAME": "",
    "ECS_TASK_JSON": json.dumps({"cluster": "someECSClusterName", "launchType": "FARGATE", "taskDefinition": "someTaskDef", "count": 1, "platformVersion": "LATEST", "networkConfiguration": {"awsvpcConfiguration": {"subnets": ["subnet-someId"], "securityGroups": ["sg-someId"], "assignPublicIp": "DISABLED"}}, "overrides": {"containerOverrides": []}})
}

class TestImports(TestCase):
    @mock.patch.dict(os.environ, TEST_ENV_VAR)
    def test_import(self):
        import src.lambda_function