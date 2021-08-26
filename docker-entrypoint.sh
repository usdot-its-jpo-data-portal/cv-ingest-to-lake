#!/bin/bash

set -e

if [ "${1:0:1}" != '-' ]; then
  exec "$@"
fi

cd /opt/src
echo 'Running ingest'

exec python -u ./lambda_function.py && exit