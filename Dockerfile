FROM python:3.8-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get purge -y --auto-remove \
    && apt-get install uuid-runtime \
    && rm -rf /var/lib/apt/lists/*

COPY docker-entrypoint.sh /opt/
COPY src /opt/src
RUN cd /opt/src \
    && pip install -r ./requirements.txt \
    && pip install boto3>=1.11.13
RUN export UUID=`uuidgen` \
    && echo 'pip install git+https://github.com/usdot-its-jpo-data-portal/sandbox_exporter@master#egg=sandbox_exporter' >> $UUID.sh \
    && sh $UUID.sh

RUN chmod +x opt/docker-entrypoint.sh
ENTRYPOINT ["opt/docker-entrypoint.sh"]