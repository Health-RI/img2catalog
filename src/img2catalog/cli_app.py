import logging
from pathlib import Path, PurePath
from typing import Dict

import click
from click_option_group import MutuallyExclusiveOptionGroup, optgroup
from rdflib import URIRef

from img2catalog.configmanager import load_img2catalog_configuration

# from xnat.client.helpers import xnatpy_login_options, connect_cli
from img2catalog.const import (
    FDP_PASS_ENV,
    FDP_SERVER_ENV,
    FDP_USER_ENV,
    VCARD,
    XNAT_HOST_ENV,
    XNAT_PASS_ENV,
    XNAT_USER_ENV,
    XNATPY_HOST_ENV,
)
from img2catalog.fdpclient import FDPClient

# Python < 3.11 does not have tomllib, but tomli provides same functionality
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import xnat

from img2catalog import log
from img2catalog.__about__ import __version__
from img2catalog.xnat_parser import xnat_to_DCATDataset, xnat_to_FDP, xnat_to_RDF

logger = logging.getLogger(__name__)


def __connect_xnat(server: str, username, password):
    """This function collects credentials and connects to XNAT

    Parameters
    ----------
    server : str
        XNAT server to connect (including https://)
    args : Namespace
        Namespace containing commandline arguments

    Returns
    -------
    XNATSession
    """
    # if not (server):
    #     if not (server := os.environ.get(XNATPY_HOST_ENV)):
    #         if not (server := os.environ.get(XNAT_HOST_ENV)):
    #             raise RuntimeError("No server specified: no argument nor environment variable found")
    # if not (username):
    #     if not (username := os.environ.get(XNAT_USER_ENV)):
    #         logger.info("No username set, using anonymous/netrc login")
    # if not (password):
    #     if not (password := os.environ.get(XNAT_PASS_ENV)):
    #         logger.info("No password set, using anonymous/netrc login")

    logger.debug("Connecting to server %s using username %s", server, username)

    session = xnat.connect(server=server, user=username, password=password)

    return session


def cli_main():
    # try:
    cli_click()
    # except Exception as e:
    #     print(f"Error running img2catalog:\n{e}")
    #     exit(-1)


# @click.command(name='dcat', help="Export XNAT to DCAT")
# @optgroup.group('Server configuration', help='The configuration of the XNAT server', required=False)
@click.group(invoke_without_command=True)
# wontfix
# https://github.com/pallets/click/issues/714
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
# @xnatpy_login_options
@click.pass_context
@click.version_option(__version__)
def cli_click(
    ctx: click.Context,
    server: str,
    username: str,
    password: str,
    config: click.Path,
    verbose: bool,
    logfile: click.Path,
    optin: str,
    optout: str,
    **kwargs,
):
    """This tool queries metadata from an XNAT server"""
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

    # with connect_cli(cli=False, **kwargs) as session:
    # If username is not environment variable and password is, that's usually not intended
    # Thus we clear password so xnatpy can deal with it
    if ctx.get_parameter_source("username") != click.core.ParameterSource.ENVIRONMENT:
        if ctx.get_parameter_source("password") == click.core.ParameterSource.ENVIRONMENT:
            password = None

    ctx.obj["xnat_conn"] = __connect_xnat(server, username, password)
    ctx.obj["config"] = config

    # output_dcat(server, username, password, output, format, config)


@cli_click.command(name="dcat")
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
def output_dcat(ctx: click.Context, output: click.Path, format: str):
    # , server, username, password, output, format, config):
    config = ctx.obj["config"]
    with ctx.obj["xnat_conn"] as session:
        logger.debug("Connected to XNAT server")
        g = xnat_to_RDF(session, config)
        logger.debug("Finished acquiring RDF graph")

    if output:
        logger.debug("Output option set, serializing output to file %s in %s format", output, format)
        g.serialize(destination=output, format=format)

    else:
        logger.debug("Sending output to stdout")
        print(g.serialize(format=format))


@click.option("-f", "--fdp", envvar=FDP_SERVER_ENV, type=str, required=True, help="URL of FDP to push to")
@click.option("-u", "--username", envvar=FDP_USER_ENV, type=str, required=True, help="Username of FDP to push to")
@click.option("-p", "--password", envvar=FDP_PASS_ENV, type=str, required=True, help="Password of FDP to push to")
@click.option("-c", "--catalog", default=None, type=URIRef, help="Catalog URI of FDP")
@cli_click.command(name="fdp")
@click.pass_context
def output_fdp(ctx: click.Context, fdp: str, username: str, password: str, catalog: URIRef):
    config = ctx.obj["config"]

    # For some reason, in testing, execution doesn't progress beyond this line
    fdpclient = FDPClient(fdp, username, password)

    if not catalog:
        if not (catalog := config["img2catalog"]["fdp"]["catalog"]):
            raise ValueError("No catalog uri set")

    with ctx.obj["xnat_conn"] as session:
        xnat_to_FDP(session, config, catalog, fdpclient)


@cli_click.command(name="project")
@click.argument("project_id", default=None, type=str)
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
def output_project(ctx: click.Context, project_id: str, output: click.Path, format: str):
    """Specify one project for DCAT extraction.

    The project is referred to by XNAT ID"""
    config = ctx.obj["config"]

    with ctx.obj["xnat_conn"] as session:
        g = xnat_to_DCATDataset(session.projects[project_id], config).to_graph(userinfo_format=VCARD.VCard)

    if output:
        logger.debug("Output option set, serializing output to file %s in %s format", output, format)
        g.serialize(destination=output, format=format)

    else:
        logger.debug("Sending output to stdout")
        print(g.serialize(format=format))


if __name__ == "__main__":
    cli_click()
