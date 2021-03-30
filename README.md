# cv_pilot_ingest
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=usdot-its-jpo-data-portal_cv_pilot_ingest&metric=alert_status)](https://sonarcloud.io/dashboard?id=usdot-its-jpo-data-portal_cv_pilot_ingest)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=usdot-its-jpo-data-portal_cv_pilot_ingest&metric=coverage)](https://sonarcloud.io/dashboard?id=usdot-its-jpo-data-portal_cv_pilot_ingest)

Utilities to work with ITS Sandbox and code for CV pilot data ingestion pipeline (ingestion into ITS Sandbox and from ITS Sandbox to Socrata). For more information on ITS Sandbox data, please refer to the [ITS Sandbox README page](https://github.com/usdot-its-jpo-data-portal/sandbox/tree/split-repo#exporting-data-to-csv-with-sandbox-exporter). For python package for working with the ITS Sandbox data, please refer to the [Sandbox Exporter](https://github.com/usdot-its-jpo-data-portal/sandbox_exporter) package.

This repository currently includes several utility scripts: S3 Folder Restructurer. These utilities uses Python 3.x as the primary programming language and should be able to be executed across operative systems. The following utility scripts have been migrated to the [Sandbox Exporter](https://github.com/usdot-its-jpo-data-portal/sandbox_exporter) package: Sandbox Exporter, Data Flattener, Socrata Connector.

**Table of Contents**

* [Utilities](#utilities)
  * [S3 Folder Restructurer](#S3-Folder-Restructurer)

## Utilities

### S3 Folder Restructurer

This utility can be used to reorganizing folder based on generatedAt timestamp.

Sample command line prompt:
```
python -u restructure_folder.py
	--bucket usdot-its-cvpilot-public-data
	--bucket_prefix usdot-its-datahub-
	--folder wydot/BSM/2018
	--outfp wydotBSM2018fps.txt
	--startKey wydot/BSM/2018/11/29/17/usdot-its-cvpilot-bsm-public-4-2018-11-29-17-54-20-2b9afefa-ff32-4b8d-b458-bed83857dd46

```
Run `python restructure_folder.py --help` for more info on each parameter.

## Release History
* 0.1.0
  * Initial version
* 1.0.0
  * Refactored to use our [sandbox_exporter](https://github.com/usdot-its-jpo-data-portal/sandbox_exporter) package to reduce duplicative code.

## Contact information
ITS DataHub Team: data.itsjpo@dot.gov
Distributed under Apache 2.0 License. See *LICENSE* for more information.

## Contributing
1. Fork it (https://github.com/usdot-its-jpo-data-portal/cv_pilot_ingest/fork)
2. Create your feature branch (git checkout -b feature/fooBar)
3. Commit your changes (git commit -am 'Add some fooBar')
4. Push to the branch (git push origin feature/fooBar)
5. Create a new Pull Request

## Known Bugs
*

## Credits and Acknowledgment
Thank you to the Department of Transportation for funding to develop this project.

## CODE.GOV Registration Info
* __Agency:__ DOT
* __Short Description:__ Utilities to work with ITS Sandbox and code for CV pilot data ingestion pipeline.
* __Status:__ Beta
* __Tags:__ transportation, connected vehicles, intelligent transportation systems, python, ITS Sandbox, Socrata
* __Labor Hours:__ 0
* __Contact Name:__ Brian Brotsos
* __Contact Phone:__ 202-366-9013
