import unittest
import os


class TestImports(unittest.TestCase):
    def test_imports(self):
        print('Temporary dummy import test for coverage config.')
        import lambda__lake_to_socrata
        import lambda__ingest_to_lake