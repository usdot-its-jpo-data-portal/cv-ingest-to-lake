# cv_pilot_ingest
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=usdot-its-jpo-data-portal_cv_pilot_ingest&metric=alert_status)](https://sonarcloud.io/dashboard?id=usdot-its-jpo-data-portal_cv_pilot_ingest)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=usdot-its-jpo-data-portal_cv_pilot_ingest&metric=coverage)](https://sonarcloud.io/dashboard?id=usdot-its-jpo-data-portal_cv_pilot_ingest)

This repository contains lambda function code for CV pilot data ingestion pipeline (ingestion into ITS Sandbox and from ITS Sandbox to Socrata). For more information on ITS Sandbox data, please refer to the [ITS Sandbox README page](https://github.com/usdot-its-jpo-data-portal/sandbox/tree/split-repo#exporting-data-to-csv-with-sandbox-exporter).

The utilities for working with the ITS Sandbox data and Socrata have been moved to the [Sandbox Exporter](https://github.com/usdot-its-jpo-data-portal/sandbox_exporter) package. Utilities that have migrated include: Sandbox Exporter, Data Flattener, and Socrata Connector.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

#### Prerequisites for AWS Lambda Deployment

If you plan to deploy the script on AWS Lambda, you need access to an AWS account and be able to assign role(s) to a lambda function. There needs to be a role that is able to invoke lambda functions and perform list/read/write actions to relevant buckets in S3.

#### Prerequisites for Local Deployment

If you plan to deploy the script on your local machine, you need the following:

1. Have access to Python 3.6+. You can check your python version by entering `python --version` and `python3 --version` in command line.
2. Have access to the command line of a machine. If you're using a Mac, the command line can be accessed via the [Terminal](https://support.apple.com/guide/terminal/welcome/mac), which comes with Mac OS. If you're using a Windows PC, the command line can be accessed via the Command Prompt, which comes with Windows, or via [Cygwin64](https://www.cygwin.com/), a suite of open source tools that allow you to run something similar to Linux on Windows.
3. Have your own Free Amazon Web Services account.
	- Create one at http://aws.amazon.com
4.  Obtain Access Keys:
	- On your Amazon account, go to your profile (at the top right)
	- My Security Credentials > Access Keys > Create New Access Key
	- Record the Access Key ID and Secret Access Key ID (you will need them in step 4)
5. Save your AWS credentials in your local machine, using one of the following method:
	- shared credentials file: instructions at https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#shared-credentials-file.
	- environmental variables: instructions at https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#environment-variables

### Installing locally

1. Download the script by cloning the git repository at https://github.com/usdot-its-jpo-data-portal/cv_pilot_ingest. You can do so by running the following in command line.
`git clone https://github.com/usdot-its-jpo-data-portal/cv_pilot_ingest.git`. If unfamiliar with how to clone a repository, follow the guide at https://help.github.com/en/articles/cloning-a-repository.
2. Navigate into the repository folder by entering `cd cv_pilot_ingest` in command line.
3. Create a virtualenv folder by running `virtualenv --python=python3 temp_env/`. If you do not have virtualenv installed, you may install it by following the [virtualenv installation instruction](https://virtualenv.pypa.io/en/latest/installation.html).
4. Activate the virtualenv by running `source temp_env/bin/activate`.
5. Install the required packages in your virtualenv by running `pip install -r requirements__ingest_to_lake.txt`, `pip install -r requirements__lake_to_socrata.txt`, and `pip install -r requirements.txt`.

### Running Tests

If this is your first time running tests, run the following line in your command line to install the required packages:
`pip install coverage "pytest<5"`

Run the test by entering the following in command line:
`coverage run -m pytest`

Run coverage report by entering the following in command line:
`coverage report -m`

## Deployment

### Deployment on AWS Lambda

1. To prepare the code package for deployment to AWS Lambda, run `sh package.sh` to build the packages. This will create two zipped files in the repo's root folder: `ingest_to_lake.zip` and `lake_to_socrata.zip`.
2. For each of the lambdas, create a lambda function in your AWS account "from scratch" with the following settings:
	- Runtime: Python 3.8
	- Permissions: Use an existing role (choose existing role with full lambda access (e.g. policy AWSLambdaFullAccess) and list/read/write permission to your destination s3 bucket)
3. In the configuration view of your lambda function, set the following:
	- For the `ingest_to_lake` function:
		- In "Function code" section, select "Upload a .zip file" and upload the `ingest_to_lake.zip` file as your "Function Package."
		- In "Environment variables" section, set the following:
			- `TARGET_BUCKET`: the destination s3 bucket (sandbox bucket).
				- default set as: usdot-its-cvpilot-public-data
		- In "Basics settings" section, set adequate Memory and Timeout values. Memory of 1664 MB and Timeout value of 10 minutes should be plenty.
		- In "Triggers" section, set the S3 bucket(s) where data provider(s) is depositing data files to trigger on Object Creation.
	- For the `lake_to_socrata` functions:
    - For these, you'll want to create one function for each pilot/message type for now. For example, you'll have separate lambdas for dealing with WYDOT TIM and WYDOT BSM.
		- In "Function code" section, select "Upload a .zip file" and upload the `lake_to_socrata.zip` file as your "Function Package."
		- In "Environment variables" section, set the following:
	    - `SOCRATA_PARAMS`: stringified json object containing Socrata credentials for a user that has write access to the WZDx feed registry. At a minimum, this should include `username`, `password`, `app_token`, and `domain`. If you do not have a `app_token` you can set it as an empty string.
      - `SOCRATA_DATASET_ID`: the 4x4 ID of the corresponding Socrata dataset the function will be updating.
		- In "Triggers" section, set the lake S3 bucket (sandbox) to trigger on Object Creation with a specified prefix. For example, for WYDOT TIM data, the prefix will be `wydot/TIM`.
		- In "Basics settings" section, set adequate Memory and Timeout values. Memory of 1664 MB and Timeout value of 10 minutes should be plenty.
4. Make sure to save all of your changes.

### Invocation of the Lambdas

All three lambda functions expect to be invoked via code.

In our deployment, the `ingest_to_lake` is invoked by deposit of data into private S3 ingestion buckets. The `lake_to_socrata` lambdas are invoked by deposit of data into the public S3 sandbox bucket under various prefixes.

### Deployment of S3 Explorer site

1. Upload `index.html` to the root folder of your S3 bucket.
2. In the AWS Console for your S3 bucket, go to "Permissions" > "CORS configuration" and copy and paste the following block of text and replace `{BUCKET_NAME}` with your bucket name.

```
<?xml version="1.0" encoding="UTF-8"?>
<CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<CORSRule>
    <AllowedOrigin>*</AllowedOrigin>
    <AllowedOrigin>http://{BUCKET_NAME}.s3.amazonaws.com</AllowedOrigin>
    <AllowedOrigin>https://s3.amazonaws.com</AllowedOrigin>
    <AllowedMethod>GET</AllowedMethod>
    <AllowedMethod>HEAD</AllowedMethod>
    <MaxAgeSeconds>3000</MaxAgeSeconds>
    <ExposeHeader>ETag</ExposeHeader>
    <ExposeHeader>x-amz-meta-custom-header</ExposeHeader>
    <AllowedHeader>Authorization</AllowedHeader>
    <AllowedHeader>*</AllowedHeader>
</CORSRule>
</CORSConfiguration>
```

3. Save. Also make sure that your bucket policy allows for List/Get actions on resource `arn:aws:s3:::{BUCKET_NAME}/*` and `arn:aws:s3:::{BUCKET_NAME}`.

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
