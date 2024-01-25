import argparse
import logging
import os
from pathlib import Path, PurePath
from typing import Dict

import click
from click_option_group import optgroup, MutuallyExclusiveOptionGroup

# from xnat.client.helpers import xnatpy_login_options, connect_cli

from xnatdcat.const import EXAMPLE_CONFIG_PATH, XNATPY_HOST_ENV, XNAT_HOST_ENV, XNAT_PASS_ENV, XNAT_USER_ENV

# Python < 3.11 does not have tomllib, but tomli provides same functionality
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import xnat

from .__about__ import __version__
from .xnat_parser import xnat_to_RDF
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


def load_configuration(config_path: Path = None) -> Dict:
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
@click.command()
@click.argument(
    "server",
    type=str,
    envvar=[XNATPY_HOST_ENV, XNAT_HOST_ENV]
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
def cli_click(server, username, password, output, format, config, verbose, logfile, optin, optout, **kwargs):
    """This tool generates DCAT from XNAT server SERVER.

    If SERVER is not specified, the environment variable [fixme] will be used"""
    log._add_file_handler(logfile)
    logger.info("======= XNATDCAT New Run ========")
    if verbose:
        log.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")

    config = load_configuration(config)

    if optin or optout:
        config['xnatdcat']['optin'] = optin
        config['xnatdcat']['optout'] = optout

    # with connect_cli(cli=False, **kwargs) as session:
    with __connect_xnat(server, username, password) as session:
        logger.debug('Connected to XNAT server')
        g = xnat_to_RDF(session, config)
        logger.debug('Finished acquiring RDF graph')

    if output:
        logger.debug("Output option set, serializing output to file %s in %s format", output, format)
        g.serialize(destination=output, format=format)
    else:
        logger.debug("Sending output to stdout")
        print(g.serialize(format=format))

    # click.abort(0)


if __name__ == "__main__":
    cli_click()
