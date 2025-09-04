# `img2catalog`: From the shelves to the spotlight

![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FHealth-RI%2Fimg2catalog%2Fmain%2Fpyproject.toml)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/Health-RI/img2catalog/python-test-package.yml)
![Codecov](https://img.shields.io/codecov/c/github/Health-RI/img2catalog)

This tool `img2catalog` is built to extract metadata from imaging data repositories, map it to a model class,
and export it to a catalog. The tool is set up to be modular, but it currently supports extracting metadata from 
an XNAT server, converting it to the [Health-RI Core v2 metadata model](https://github.com/Health-RI/health-ri-metadata/tree/v2.0.0),
based on DCAT-AP v3 and Health-DCAT AP,
as defined in Pydantic classes using [SeMPyRO](https://github.com/Health-RI/SeMPyRO), and either writing it 
to an RDF file, or pushing it to a [FAIR Data Point (FDP)](https://www.fairdatapoint.org/).

## Installation

`img2catalog` requires an installation of Python 3.8 or higher. It can be installed by running

```shell
pip install img2catalog
```

## Usage

`img2catalog` consists of:
- an input,
- a mapping,
- and an output.

A basic example:
```shell 
img2catalog xnat --server https://xnat.bmia.nl map-xnat-hriv2 rdf
```
In this example we use the input `xnat`, that connects to the server `https://xnat.health-ri.nl`,
uses the mapping `map-xnat-hriv2` that maps the extracted metadata to the Health-RI Core v2 metadata model, 
and serializes that to RDF and outputs it to the terminal using the output `rdf`. 

In this mapping the XNAT itself will be converted to a Catalog object, and the projects to Datasets.

### Pushing to a FAIR Data Point (FDP)

Using `img2catalog` one can directly push the Datasets created from XNAT projects to an existing Catalog on an FDP. 
To do so, run the following command with the output `fdp`:

```shell 
img2catalog xnat --server https://xnat.bmia.nl map-xnat-hriv2 fdp --fdp "https://fdp.healthdata.nl" -u "albert.einstein@example.com" -p "password" -c "https://fdp-acc.healthdata.nl/catalog/5400322c-273c-4f47-ae30-00e7c345b85d"
```
This will add the new Datasets to the Catalog. In order to update the Datasets on the FAIR Data Point when rerunning 
`img2catalog`, it is necessary to first perform a SPARQL query on the GraphDB, or another triple store, that contains
the metadata stored in your FDP. To do so, supply the SPARQL endpoint as an argument to the `fdp` output.

```sh
img2catalog xnat --server https://xnat.bmia.nl map-xnat-hriv2 fdp --fdp "https://fdp.healthdata.nl" -u "albert.einstein@example.com" -p "password" -c "https://fdp-acc.healthdata.nl/catalog/5400322c-273c-4f47-ae30-00e7c345b85d" -s "https://sparql-acc.healthdata.nl/repositories/fdp"
```   

### Configuration

A number of configuration option are available through the command line interface (CLI). To get an overview of these
options, run `img2catalog --help` and on any subsequent submodules, e.g., `img2catalog xnat`.

An example configuration file `config.toml` is supplied with this project. By default, `img2catalog`
will use the configuration file `~/.img2catalog/config.toml`, if it exists.
If the file does not exist, a default configuration will be used.

Currently, it is not possible to gather all the information for the Health-RI v2 model from a regular XNAT project.
Additional properties can be stored in XNAT using XNAT Custom Forms. A JSON definition for the form for the Health-RI v2.0.0 model
can be found in `./ext/xnat_custom_forms/health-ri-v2-dataset.json`. This form can be attached to a project and the information can be 
retrieved by supplying the form ID in the configuration, like so:
```toml
[xnat]
dataset_form_id = "48660455-b964-4aef-b293-fbc1fab96bc0"
```
The metadata can be supplemented by defining fallback values in the configuration file. 

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

### Authentication

Authentication for XNAT can be done using, in order of precedence:
- Command line arguments
- Environment variables
- `.netrc` file.

For more information regarding this, see the [XNATpy documentation](https://xnat.readthedocs.io/en/latest/static/tutorial.html#credentials).

## Inclusion and exclusion of projects

By default, all public and protected projects are indexed. 
Since private projects are not shown on XNAT, they will also not be harvested to be represented in a public 
catalogue.

By specifying either opt-in or opt-out keywords, projects can be included and excluded.
If an opt-in keyword is given, only projects with that keyword are included; if an opt-out keyword is given
all projects except those with that keyword are included. If none are supplied, all projects will be included;
if both opt-in and opt-out keywords are given, then only the opt-in keyword is applied.

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
