import logging
from pathlib import Path

import click
import xnat
from click_option_group import MutuallyExclusiveOptionGroup, optgroup
from rdflib import URIRef
from xnat import XNATSession

from img2catalog import log
from img2catalog.__about__ import __version__
from img2catalog.configmanager import load_img2catalog_configuration

from img2catalog.const import (
    FDP_PASS_ENV,
    FDP_SERVER_ENV,
    FDP_USER_ENV,
    XNAT_HOST_ENV,
    XNAT_PASS_ENV,
    XNAT_USER_ENV,
    XNATPY_HOST_ENV,
    SPARQL_ENV,
)
from img2catalog.inputs.config import ConfigInput
from img2catalog.inputs.xnat import XNATInput
from img2catalog.mappings.xnat import map_xnat_to_healthriv2
from img2catalog.outputs.fdp import FDPOutput
from img2catalog.outputs.rdf import RDFOutput


logger = logging.getLogger(__name__)

def __connect_xnat(server: str, username: str, password: str) -> XNATSession:
    """This function collects credentials and connects to XNAT

    Parameters
    ----------
    server : str
        XNAT server to connect (including https://)
    username: str
        Username of XNAT user
    password: str
         Password of XNAT user

    Returns
    -------
    XNATSession
    """

    logger.debug("Connecting to server %s using username %s", server, username)

    session = xnat.connect(server=server, user=username, password=password)

    return session


@click.group(invoke_without_command=True)
# wontfix
# https://github.com/pallets/click/issues/714
@click.option(
    "-c",
    "--config",
    default=None,
    type=click.Path(exists=True, path_type=Path, readable=True),
    help="Configuration file to use. If not set, will use ~/.img2catalog/config.toml if it exists.",
)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Enables debugging mode.")
@click.option(
    "-l",
    "--logfile",
    default="./img2catalog.log",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path, writable=True),
    help="Path of logfile to use. Default is img2catalog.log in current directory",
)
@optgroup(cls=MutuallyExclusiveOptionGroup)
@optgroup.option(
    # Both opt-in and opt-out at the same time is not very logical, so it is not allowed.
    "--optin",
    type=str,
    help="Opt-in keyword. If set, only projects with this keyword will be included",
    default=None,
)
@optgroup.option(
    "--optout", type=str, help="Opt-out keyword. If set, projects with this keyword will be excluded", default=None
)
@click.pass_context
@click.version_option(__version__)
def cli_click(
    ctx: click.Context,
    config: click.Path,
    verbose: bool,
    logfile: click.Path,
    optin: str,
    optout: str,
    **kwargs,
):
    """Extract metadata from an imaging data repository."""
    ctx.ensure_object(dict)
    log._add_file_handler(logfile)
    logger.info("======= img2catalog New Run ========")
    if verbose:
        log.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")

    config = load_img2catalog_configuration(config)

    if optin or optout:
        config["img2catalog"]["optin"] = optin
        config["img2catalog"]["optout"] = optout

    ctx.obj["config"] = config


@click.group(name="xnat")
@click.option(
    "-s",
    "--server",
    type=str,
    envvar=[XNATPY_HOST_ENV, XNAT_HOST_ENV],
    required=True,
    help=f"URI of the server to connect to (including http:// or https://). If not set, will use environment variables {XNATPY_HOST_ENV} or {XNAT_HOST_ENV}.",
)
@click.option(
    "-u",
    "--username",
    type=str,
    default=None,
    envvar=XNAT_USER_ENV,
    help=f"Username to use, leave empty to use netrc entry or anonymous login or environment variable {XNAT_USER_ENV}.",
)
@click.option(
    "-p",
    "--password",
    type=str,
    default=None,
    envvar=XNAT_PASS_ENV,
    help=(
            "Password to use with the username, leave empty when using netrc. If a"
            " username is given and no password or environment variable, there will be a prompt on the console"
            f" requesting the password. Environment variable: {XNAT_PASS_ENV}"
    ),
)
@click.pass_context
def input_xnat(ctx: click.Context, server: str, username: str, password: str):
    """ Extract metadata from the projects on an XNAT server."""
    config = ctx.obj['config']
    # If username is not environment variable and password is, that's usually not intended
    # Thus we clear password so xnatpy can deal with it
    if ctx.get_parameter_source("username") != click.core.ParameterSource.ENVIRONMENT:
        if ctx.get_parameter_source("password") == click.core.ParameterSource.ENVIRONMENT:
            password = None

    ctx.obj["xnat_conn"] = __connect_xnat(server, username, password)

    with ctx.obj["xnat_conn"] as session:
        logger.debug("Connected to XNAT server")
        xnat_input = XNATInput(config, session)
        config_input = ConfigInput(config)
        unmapped_objects = xnat_input.get_and_update_metadata(config_input)
    ctx.obj['unmapped_objects'] = unmapped_objects

cli_click.add_command(input_xnat)


@click.group("map-xnat-hriv2")
@click.pass_context
def mapping_xnat_healthriv2(ctx: click.Context):
    """ Map metadata from XNAT to the Health-RI v2 model."""
    unmapped_objects = ctx.obj['unmapped_objects']

    mapped_objects = map_xnat_to_healthriv2(unmapped_objects)

    ctx.obj['mapped_objects'] = mapped_objects

input_xnat.add_command(mapping_xnat_healthriv2)


@mapping_xnat_healthriv2.command(name="rdf")
@click.option(
    "-o",
    "--output",
    "output",
    default=None,
    type=click.Path(writable=True, dir_okay=False),
    help="Destination file to write output to. If not set, the script will print serialized output to stdout.",
)
@click.option(
    "-f",
    "--format",
    default="turtle",
    type=click.Choice(
        ["xml", "n3", "turtle", "nt", "pretty-xml", "trix", "trig", "nquads", "json-ld", "hext"], case_sensitive=False
    ),
    help=(
        "The format that the output should be written in. This value references a"
        " Serializer plugin in RDFlib. Supportd values are: "
        ' "xml", "n3", "turtle", "nt", "pretty-xml", "trix", "trig", "nquads",'
        ' "json-ld" and "hext". Defaults to "turtle".'
    ),
)
@click.pass_context
def output_rdf(ctx: click.Context, output: click.Path, format: str):
    """ Serialize metadata to RDF, either to file or stdout. """
    config = ctx.obj["config"]
    mapped_objects = ctx.obj['mapped_objects']

    rdf_output = RDFOutput(config, format)

    if output:
        rdf_output.to_file(mapped_objects, output)

    else:
        rdf_output.to_stdout(mapped_objects)


@click.option("-f", "--fdp", envvar=FDP_SERVER_ENV, type=str, required=True, help="URL of FDP to push datasets to")
@click.option("-u", "--username", envvar=FDP_USER_ENV, type=str, required=True, help="Username of FDP to push to")
@click.option("-p", "--password", envvar=FDP_PASS_ENV, type=str, required=True, help="Password of FDP to push to")
@click.option(
    "-c", "--catalog", default=None, type=URIRef, help="Catalog URI where datasets will be placed in", required=True
)
@click.option(
    "-s",
    "--sparql",
    envvar=SPARQL_ENV,
    type=URIRef,
    help=" URL of SPARQL endpoint of FDP, used for querying which dataset to update",
)
@mapping_xnat_healthriv2.command(name="fdp")
@click.pass_context
def output_fdp(ctx: click.Context, fdp: str, username: str, password: str, catalog: URIRef, sparql: str):
    """ Push metadata to a FAIR Data Point (FDP). """
    config = ctx.obj["config"]
    mapped_objects = ctx.obj['mapped_objects']

    fdp_output = FDPOutput(config, fdp, username, password,
                           catalog_uri=catalog, sparql=sparql)

    fdp_output.push_to_fdp(mapped_objects)


@click.group(name="xnat-project")
@click.argument("project_id", default=None, type=str)
@click.option(
    "-s",
    "--server",
    type=str,
    envvar=[XNATPY_HOST_ENV, XNAT_HOST_ENV],
    required=True,
    help=f"URI of the server to connect to (including http:// or https://). If not set, will use environment variables {XNATPY_HOST_ENV} or {XNAT_HOST_ENV}.",
)
@click.option(
    "-u",
    "--username",
    type=str,
    default=None,
    envvar=XNAT_USER_ENV,
    help=f"Username to use, leave empty to use netrc entry or anonymous login or environment variable {XNAT_USER_ENV}.",
)
@click.option(
    "-p",
    "--password",
    type=str,
    default=None,
    envvar=XNAT_PASS_ENV,
    help=(
            "Password to use with the username, leave empty when using netrc. If a"
            " username is given and no password or environment variable, there will be a prompt on the console"
            f" requesting the password. Environment variable: {XNAT_PASS_ENV}"
    ),
)
@click.pass_context
def input_xnat_project(ctx: click.Context, project_id: str, server: str, username: str, password: str):
    """ Extract metadata from one XNAT project.

     The XNAT project is specified by project ID."""
    config = ctx.obj["config"]
    # If username is not environment variable and password is, that's usually not intended
    # Thus we clear password so xnatpy can deal with it
    if ctx.get_parameter_source("username") != click.core.ParameterSource.ENVIRONMENT:
        if ctx.get_parameter_source("password") == click.core.ParameterSource.ENVIRONMENT:
            password = None

    ctx.obj["xnat_conn"] = __connect_xnat(server, username, password)

    with ctx.obj["xnat_conn"] as session:
        project = session.projects[project_id]
        logger.debug("Connected to XNAT server")
        xnat_input = XNATInput(config, session)
        config_input = ConfigInput(config)

        xnat_catalog = xnat_input.get_metadata_catalogs()
        config_catalog = config_input.get_metadata_concept('catalog')
        xnat_catalog = config_input.update_metadata(xnat_catalog, config_catalog)

        xnat_datasets = [xnat_input.project_to_dataset(project)]
        config_dataset = config_input.get_metadata_concept('dataset')
        xnat_datasets = config_input.update_metadata(xnat_datasets, config_dataset)

    unmapped_objects = {
        'catalog': xnat_catalog,
        'dataset': xnat_datasets
    }
    ctx.obj['unmapped_objects'] = unmapped_objects


cli_click.add_command(input_xnat_project)
input_xnat_project.add_command(mapping_xnat_healthriv2)


if __name__ == "__main__":
    cli_click()
