# XNAT to DCAT-AP

![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FHealth-RI%2Fimg2catalog%2Fmain%2Fpyproject.toml)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/Health-RI/img2catalog/python-test-package.yml)
![Codecov](https://img.shields.io/codecov/c/github/Health-RI/img2catalog)

This tool queries an XNAT instance and generates DCAT-AP 3.0 metadata. Every XNAT project is
considered to be a separate Dataset. Only 'public' and 'protected' datasets are queried.

The metadata is compliant with the [Health-RI core v1 specification](https://github.com/Health-RI/health-ri-metadata/).
Some fields are still left as placeholders. These will be updated in due time.

## Installation

This tool requires an installation of Python 3.8 or higher.
Download a wheel file from releases and install using `pip install`. The tool can then be run by
running the `img2catalog` command from the commandline.

## Usage

Basic example: `img2catalog https://xnat.bmia.nl`; output will appear at stdout. A log file `img2catalog.log` will be
created in the directory from which you run this program.

The tool supports both public and private XNAT instances. For authentication, you can either supply
a username and/or password at the commandline or use a `.netrc` file. For more information regarding
this, see the [XNATpy documentation](https://xnat.readthedocs.io/en/latest/static/tutorial.html#credentials).

By default, output of the tool is in turtle format at stdout to make for easy piping, but it can be
written in a variety of formats to a file, too. For all options, see `img2catalog --help`:

```sh
Usage: img2catalog [OPTIONS] COMMAND [ARGS]...

  This tool queries metadata from an XNAT server

Options:
  -s, --server TEXT      URI of the server to connect to (including http:// or
                         https://). If not set, will use environment variables
                         XNATPY_HOST or XNAT_HOST.  [required]
  -u, --username TEXT    Username to use, leave empty to use netrc entry or
                         anonymous login or environment variable XNAT_USER.
  -p, --password TEXT    Password to use with the username, leave empty when
                         using netrc. If a username is given and no password
                         or environment variable, there will be a prompt on
                         the console requesting the password. Environment
                         variable: XNAT_PASS
  -c, --config PATH      Configuration file to use. If not set, will use
                         ~/.img2catalog/config.toml if it exists.
  -v, --verbose          Enables debugging mode.
  -l, --logfile FILE     Path of logfile to use. Default is img2catalog.log in
                         current directory
  [mutually_exclusive]:
    --optin TEXT         Opt-in keyword. If set, only projects with this
                         keyword will be included
    --optout TEXT        Opt-out keyword. If set, projects with this keyword
                         will be excluded
  --version              Show the version and exit.
  --help                 Show this message and exit.

Commands:
  dcat
  fdp


Usage: img2catalog dcat [OPTIONS]

Options:
  -o, --output FILE               Destination file to write output to. If not
                                  set, the script will print serialized output
                                  to stdout.
  -f, --format [xml|n3|turtle|nt|pretty-xml|trix|trig|nquads|json-ld|hext]
                                  The format that the output should be written
                                  in. This value references a Serializer
                                  plugin in RDFlib. Supportd values are:
                                  "xml", "n3", "turtle", "nt", "pretty-xml",
                                  "trix", "trig", "nquads", "json-ld" and
                                  "hext". Defaults to "turtle".
  --help                          Show this message and exit.

Usage: img2catalog fdp [OPTIONS]

Options:
  -s, --sparql URIREF   URL of SPARQL endpoint of FDP, used for querying which
                        dataset to update
  -c, --catalog URIREF  Catalog URI where datasets will be placed in
                        [required]
  -p, --password TEXT   Password of FDP to push to  [required]
  -u, --username TEXT   Username of FDP to push to  [required]
  -f, --fdp TEXT        URL of FDP to push datasets to  [required]
  --help                Show this message and exit.

```

### Example with SPARQL endpoint

```sh
img2catalog --verbose -s "https://xnat-acc.health-ri.nl" fdp --fdp "https://fdp-acc.healthdata.nl" -u "albert.einstein@example.com" -p "check 1 Password" -c "https://fdp-acc.healthdata.nl/catalog/5400322c-273c-4f47-ae30-00e7c345b85d" -s "https://sparql-acc.healthdata.nl/repositories/fdp"
```   

## Configuration

An example configuration file `config.toml` is supplied with this project. By default, `img2catalog`
will look for a configuration file in `~/.img2catalog/config.toml`. The tool will not create the file
or folder if it does not exist, you will have to do so manually. If the file does not exist, a
hard-coded example file will be used.

A limited number of properties can be set in the configuration, including the title and name of the
xnat (DCAT) catalog and the publisher of the catalog. A default contact point for datasets can also
be provided and will be included in the Dataset properties.

The tool can also be configured using environment variables. Here are the environment variables that can be used:

### Environment Variables

The tool can also be configured using environment variables. Here are the environment variables that can be used:
* XNAT_HOST: The XNAT server host.
* XNATPY_HOST: Alternative environment variable for the XNAT server host.
* XNAT_USER: The XNAT username.
* XNAT_PASS: The XNAT password.
* IMG2CATALOG_FDP: The FDP server.
* IMG2CATALOG_FDP_USER: The FDP username.
* IMG2CATALOG_FDP_PASS: The FDP password.
* IMG2CATALOG_SPARQL_ENDPOINT: The SPARQL endpoint.

Commandline arguments take precedence over environment variables. Environment variables take
precedence over `.netrc` login.

## Metadata

THe current metadata complies to the Health-RI core v1 shapes. This is an extension of DCAT-AP,
output of the tool is thus fully compliant with DCAT-AP. A few fields that cannot be extracted
from XNAT, are set at a more global level. This includes *dcat:contactPoint*, *dcat:theme* and
*dcat:publisher*. The value of those fields can be set in the configuration.

A few fields are currently set with stub values. That includes the *dcterms:identifier* of the
*creator*, the *dcterms:license*, and the *dcterms:issued* and *dcterms:modified* fields. We hope
to be able to expand XNAT to include these fields as well.

## Inclusion and exclusion of projects

By default, all public and protected projects are indexed. Private projects are *not* indexed, even
if you provide user credentials that have relevant permissions for them. We can make an override
for this behavior, please file an issue if you'd like to see this changed.

Further granularity can be provided by using keywords. There is functionality for an opt-in keyword
and an opt-out keyword, though only one of these at the time. If an opt-in keyword is set, only
projects containing this magic keyword in their metadata will be indexed. All other projects will be
ignored. If an opt-out keyword is set, all projects except for those containing the magic opt-out
keyword will be indexed. The keywords can be configured in either the settings or the CLI, see the
example configuration file.

Note that private projects will currently not be indexed, not even if an opt-in keyword is set in them.

## Development

This project uses [Hatch](https://hatch.pypa.io/latest/) as a project manager. After cloning the
repository, the development version can be run by `hatch run img2catalog`. Hatch will take care of
dependencies and all of that.

You can run unit tests by running `hatch run test:test`, or get in a shell in the python environment by
running `hatch shell`. Hatch uses whatever Python version is currently loaded.
This project is compatible with Python 3.8 and up.

Pull requests are very much welcomed! As long the output remains at least DCAT-AP v3 compliant,
we are open to any additions.

## Limitations

Currently, title, description, keywords, PI and Investigators are set as well as title, description
and publisher of the catalogue. There is no Distribution, Dataset Series or anything else.
The language of the fields also is not set.

## Disclaimer

![Emblem co-funded by the European Union](/ext/EN_Co-fundedbytheEU_RGB_POS.png)
This project is co-funded by the European Union under Grant Agreement 101100633. Views and opinions
expressed are however those of the author(s) only and do not necessarily reflect those of the
European Union or the European Commission. Neither the European Union nor the granting authority can
be held responsible for them.
