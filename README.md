# XNAT to DCAT-AP

![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FHealth-RI%2Fxnatdcat%2Fmain%2Fpyproject.toml)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/Health-RI/xnatdcat/python-test-package.yml)
![Codecov](https://img.shields.io/codecov/c/github/Health-RI/xnatdcat)

This tool queries an XNAT instance and generates DCAT-AP 3.0 metadata. Every XNAT project is considered
to be a separate Dataset. Only 'public' and 'protected' datasets are queried.

## Installation

This tool requires an installation of Python 3.8 or higher.
Download a wheel file from releases and install using `pip install`. The tool can then be run by
running the `xnatdcat` command from the commandline.

## Usage

Basic example: `xnatdcat https://xnat.bmia.nl`; output will appear at stdout. A log file `xnatdcat.log` will be
created in the directory from which you run this program.

The tool supports both public and private XNAT instances. For authentication, you can either supply
a username and/or password at the commandline or use a `.netrc` file. For more information regarding
this, see the [XNATpy documentation](https://xnat.readthedocs.io/en/latest/static/tutorial.html#credentials).

By default, output of the tool is in turtle format at stdout to make for easy piping, but it can be
written in a variety of formats to a file, too. For all options, see `xnatdcat --help`:

```text
usage: xnatdcat [-h] [-u USERNAME] [-p PASSWORD] [-o OUTPUT] [-f FORMAT] [-c CONFIG] [-V] [server]

This tool generates DCAT from XNAT

positional arguments:
  server                URI of the server to connect to (including http:// or https://). If not
                        set, will use environment variables.

options:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        Username to use, leave empty to use netrc entry or anonymous login or
                        environment variables.
  -p PASSWORD, --password PASSWORD
                        Password to use with the username, leave empty when using netrc. If a
                        username is given and no password or environment variable, there will be a
                        prompt on the console requesting the password.
  -o OUTPUT, --output OUTPUT
                        Destination file to write output to. If not set, the script will print
                        serialized output to stdout.
  -f FORMAT, --format FORMAT
                        The format that the output should be written in. This value references a
                        Serializer plugin in RDFlib. Supportd values are: "xml", "n3", "turtle",
                        "nt", "pretty-xml", "trix", "trig", "nquads", "json-ld" and "hext".
                        Defaults to "turtle".
  -c CONFIG, --config CONFIG
                        Configuration file to use. If not set, will use ~/.xnatdcat/config.toml if
                        it exists.
  -V, --version         show program's version number and exit
```

## Configuration

An example configuration file `config.toml` is supplied with this project. By default, `xnatdcat`
will look for a configuration file in `~/.xnatdcat/config.toml`. The tool will not create the file
or folder if it does not exist, you will have to do so manually. If the file does not exist, the
example file will be used.

A limited number of properties can be set in the configuration, including the title and name of the
xnat (DCAT) catalog and the publisher of the catalog. We are still working on adding more default
values for certain DCAT properties to the configuration.

There is limited support for using environment variables. For setting the XNAT server, variables
`XNAT_HOST` or `XNATPY_HOST` can be used, with the latter taking preference. Authentication can be
provided in `XNAT_USER` and `XNAT_PASS`.

Commandline arguments take precedence over environment variables. Environment variables take
precedence over `.netrc` login.

## Inclusion and exclusion of projects

By default, all public and protected projects are indexed. Private projects are *not* indexed, even
if you provide user credentials that have relevant permissions for them.

Further granularity can be provided by using keywords. There is functionality for an opt-in keyword
and an opt-out keyword, though only one of these at the time. If an opt-in keyword is set, only
projects containing this magic keyword in their metadata will be indexed. All other projects will be
ignored. If an opt-out keyword is set, all projects except for those containing the magic opt-out
keyword will be indexed. The keywords can be configured in either the settings or the CLI, see the
example configuration file.

Note that private projects will never be indexed, not even if an opt-in keyword is set in them.

## Development

This project uses [Hatch](https://hatch.pypa.io/latest/) as a project manager. After cloning the
repository, the development version can be run by `hatch run xnatdcat`. Hatch will take care of
dependencies and all of that.

You can run unit tests by running `hatch run test`, or get in a shell in the python environment by
running `hatch shell`. Hatch uses whatever Python version is currently loaded.
This project is compatible with Python 3.8 and up.

Pull requests are very much welcomed! As long the output remains at least DCAT-AP v3 compliant,
we are open to any additions.

## Limitations

Currently, only title, description, keywords and PI are set as well as title, description and
publisher of the catalogue. There is no Distribution, Dataset Series or anything else. The output
does not conform to the Fair Data Point (FDP) specifications yet, but is DCAT-AP 3.0 compliant.
The language of the fields also is not set.
