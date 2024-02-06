import argparse
import logging
import os
from pathlib import Path, PurePath
from typing import Dict

import click
from rdflib import URIRef
from click_option_group import optgroup, MutuallyExclusiveOptionGroup

# from xnat.client.helpers import xnatpy_login_options, connect_cli

from xnatdcat.const import EXAMPLE_CONFIG_PATH, XNATPY_HOST_ENV, XNAT_HOST_ENV, XNAT_PASS_ENV, XNAT_USER_ENV
from xnatdcat.fdpclient import FDPClient

# Python < 3.11 does not have tomllib, but tomli provides same functionality
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import xnat

from .__about__ import __version__
from .xnat_parser import xnat_to_FDP, xnat_to_RDF
from . import log

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


def load_xnatdcat_configuration(config_path: Path = None) -> Dict:
    """Loads a configuration file for XNATDCAT

    First, it checks if config_path is given. If not, it will look for ~/.xnatdcat/config.toml,
    if that file also doesn't exist it will load an example configuration from the project rootfolder.

    Parameters
    ----------
    config_path : Path, optional
        Path to configuration file to load, by default None

    Returns
    -------
    Dict
        Dictionary with loaded configuration properties

    Raises
    ------
    FileNotFoundError
        If config_path is specified yet does not exist
    """
    if config_path:
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file does not exist at {config_path}")
    elif (config_path := Path.home() / ".xnatdcat" / "config.toml").exists():
        pass
    else:
        # Python 3.8 does not support slicing of paths yet :(
        config_path = EXAMPLE_CONFIG_PATH
        logger.warning("No configuration file found or specified! xnatdcat will use the example file.")

    logger.info("Using configuration file %s", config_path)

    with open(config_path, 'rb') as f:
        config = tomllib.load(f)

    return config


def cli_main():
    # try:
    cli_click()
    # except Exception as e:
    #     print(f"Error running xnatdcat:\n{e}")
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
    # help="URI of the server to connect to (including http:// or https://). If not set, will use environment variables.",
)
@click.option(
    "-u",
    "--username",
    type=str,
    default=None,
    envvar=XNAT_USER_ENV,
    help="Username to use, leave empty to use netrc entry or anonymous login or environment variables.",
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
        " requesting the password."
    ),
)
@click.option(
    "-c",
    "--config",
    default=None,
    type=click.Path(exists=True, path_type=Path, readable=True),
    help="Configuration file to use. If not set, will use ~/.xnatdcat/config.toml if it exists.",
)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Enables debugging mode.")
@click.option(
    "-l",
    "--logfile",
    default="./xnatdcat.log",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path, writable=True),
    help="Path of logfile to use. Default is xnatdcat.log in current directory",
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
def cli_click(ctx, server, username, password, config, verbose, logfile, optin, optout, **kwargs):
    """This tool generates DCAT from XNAT server SERVER.

    If SERVER is not specified, the environment variable [fixme] will be used"""
    ctx.ensure_object(dict)
    log._add_file_handler(logfile)
    logger.info("======= XNATDCAT New Run ========")
    if verbose:
        log.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")

    config = load_xnatdcat_configuration(config)

    if optin or optout:
        config['xnatdcat']['optin'] = optin
        config['xnatdcat']['optout'] = optout

    # with connect_cli(cli=False, **kwargs) as session:
    # If username is not environment variable and password is, that's usually not intended
    # Thus we clear password so xnatpy can deal with it
    if ctx.get_parameter_source("username") != click.core.ParameterSource.ENVIRONMENT:
        if ctx.get_parameter_source("password") == click.core.ParameterSource.ENVIRONMENT:
            password = None

    ctx.obj['xnat_conn'] = __connect_xnat(server, username, password)
    ctx.obj['config'] = config
    # output_dcat(server, username, password, output, format, config)


@cli_click.command(name='dcat')
@click.option(
    '-o',
    '--output',
    'output',
    default=None,
    type=click.Path(writable=True, dir_okay=False),
    help="Destination file to write output to. If not set, the script will print serialized output to stdout.",
)
@click.option(
    "-f",
    "--format",
    default="turtle",
    type=click.Choice(
        ['xml', 'n3', 'turtle', 'nt', 'pretty-xml', 'trix', 'trig', 'nquads', 'json-ld', 'hext'], case_sensitive=False
    ),
    help=(
        "The format that the output should be written in. This value references a"
        " Serializer plugin in RDFlib. Supportd values are: "
        " \"xml\", \"n3\", \"turtle\", \"nt\", \"pretty-xml\", \"trix\", \"trig\", \"nquads\","
        " \"json-ld\" and \"hext\". Defaults to \"turtle\"."
    ),
)
@click.pass_context
def output_dcat(ctx, output, format):
    # , server, username, password, output, format, config):
    config = ctx.obj['config']
    with ctx.obj['xnat_conn'] as session:
        logger.debug('Connected to XNAT server')
        g = xnat_to_RDF(session, config)
        logger.debug('Finished acquiring RDF graph')

    if output:
        logger.debug("Output option set, serializing output to file %s in %s format", output, format)
        g.serialize(destination=output, format=format)

    else:
        logger.debug("Sending output to stdout")
        print(g.serialize(format=format))


@click.option("--fdp", envvar='XNATDCAT_FDP', type=str, required=True, help="URL of FDP to push to")
@click.option("--fdp_user", envvar='XNATDCAT_FDP_USER', type=str, required=True, help="Username of FDP to push to")
@click.option("--fdp_pass", envvar='XNATDCAT_FDP_PASS', type=str, required=True, help="Password of FDP to push to")
@click.option("-fdp_catalog", default=None, type=URIRef, help="Catalog URI of FDP")
@cli_click.command(name='fdp')
@click.pass_context
def output_fdp(ctx, fdp, fdp_user, fdp_pass, catalog_uri):
    config = ctx.obj['config']
    fdpclient = FDPClient(fdp, fdp_user, fdp_pass)

    if not catalog_uri:
        if not (catalog_uri := config['xnatdcat']['fdp']['catalog']):
            raise ValueError("No catalog uri set")
    with ctx.obj['xnat_conn'] as session:
        xnat_to_FDP(session, config, catalog_uri, fdpclient)


if __name__ == "__main__":
    cli_click()
