#!/bin/bash
echo "Remove current package ingest_to_lake.zip"
rm -rf ingest_to_lake.zip
pip install -r src/requirements.txt --upgrade --target package/
cp src/lambda_function.py package/
cd package && zip -r ../ingest_to_lake.zip * && cd ..
rm -rf package
echo "Created package in ingest_to_lake.zip"