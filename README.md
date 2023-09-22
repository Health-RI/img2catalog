# XNAT to DCAT-AP

This tool queries an XNAT instance and generates DCAT-AP metadata. Every XNAT project is considered
to be a separate Dataset.

## Usage

Make sure all requirements are installed (see `requirements.txt`).

The script can be run from the commandline. To test, run the following command:

`python xnat_dcat.py https://xnat.bmia.nl`

For other / private XNAT instances, you can set a username and password.

More information regarding the usage of the tool, run it using the `-h` or `--help` argument.

## Limitations

Currently, only title, description and keywords are set. Only Datasets are generated. There is no
overarching Catalogue, Distribution, Dataset Series or anything else. The output does not conform
 to the Fair Data Point (FDP) specifications yet. The language of the fields also is not set.
