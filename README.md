# XNAT to DCAT-AP

This tool queries an XNAT instance and generates DCAT-AP metadata. Every XNAT project is considered
to be a separate Dataset.

## Installation

Download a wheel file from releases and install using `pip install`. The tool can then be run by
running the `xnatdcat` command from the commandline.

The tool supports both public and privat XNAT instances. For authentication, you can either supply
a username and/or password at the commandline or use a `.netrc` file. For more information regarding
this, see the [XNATpy documentation](https://xnat.readthedocs.io/en/latest/static/tutorial.html#credentials).

By default, output of the tool is in turtle format at stdout to make for easy piping, but it can be
written in a variety of formats to a file, too. For all options, see `xnatdcat --help`:

```text
usage: XNAT to DCAT [-h] [-u USERNAME] [-p PASSWORD] [-o OUTPUT] [-f FORMAT] server

This tool generates DCAT from XNAT

positional arguments:
  server                URI of the server to connect to (including http:// or https://)

optional arguments:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        Username to use, leave empty to use netrc entry or anonymous login.
  -p PASSWORD, --password PASSWORD
                        Password to use with the username, leave empty when using netrc. If a username is given and no
                        password, there will be a prompt on the console requesting the password.
  -o OUTPUT, --output OUTPUT
                        Destination file to write output to. If not set, the script will print serialized output to
                        stdout.
  -f FORMAT, --format FORMAT
                        The format that the output should be written in. This value references a Serializer plugin in
                        RDFlib. Supportd values are: "xml", "n3", "turtle", "nt", "pretty-xml", "trix", "trig",
                        "nquads", "json-ld" and "hext". Defaults to "turtle".
```

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

Currently, only title, description, keywords and PI are set. There is no overarching Catalogue,
Distribution, Dataset Series or anything else. The output does not conform to the Fair Data Point
(FDP) specifications yet, but is DCAT-AP v3 compliant. The language of the fields also is not set.
