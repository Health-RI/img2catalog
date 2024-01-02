import argparse
import logging
import os
from pathlib import Path, PurePath
from typing import Dict

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


def __parse_cli_args():
    """Simple argument parser for commandline args"""

    parser = argparse.ArgumentParser(prog="xnatdcat", description="This tool generates DCAT from XNAT")
    parser.add_argument(
        "server",
        type=str,
        help=(
            "URI of the server to connect to (including http:// or https://). If not set, will use "
            "environment variables."
        ),
        nargs="?",
    )
    parser.add_argument(
        "-u",
        "--username",
        default=None,
        type=str,
        help="Username to use, leave empty to use netrc entry or anonymous login or environment variables.",
    )
    parser.add_argument(
        "-p",
        "--password",
        default=None,
        type=str,
        help=(
            "Password to use with the username, leave empty when using netrc. If a"
            " username is given and no password or environment variable, there will be a prompt on the console"
            " requesting the password."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        type=PurePath,
        help="Destination file to write output to. If not set, the script will print serialized output to stdout.",
    )
    parser.add_argument(
        "-f",
        "--format",
        default="turtle",
        type=str,
        help=(
            "The format that the output should be written in. This value references a"
            " Serializer plugin in RDFlib. Supportd values are: "
            " \"xml\", \"n3\", \"turtle\", \"nt\", \"pretty-xml\", \"trix\", \"trig\", \"nquads\","
            " \"json-ld\" and \"hext\". Defaults to \"turtle\"."
        ),
    )
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        type=Path,
        help="Configuration file to use. If not set, will use ~/.xnatdcat/config.toml if it exists.",
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")

    parser.add_argument("-v", "--verbose", action="store_true", help="Enables debugging mode.")

    parser.add_argument(
        "-l",
        "--logfile",
        default="./xnatdcat.log",
        type=Path,
        help="Path of logfile to use. Default is xnatdcat.log in current directory",
    )

    # Both opt-in and opt-out at the same time is not very logical, so it is not allowed.
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--optin",
        type=str,
        help="Opt-in keyword. If set, only projects with this keyword will be included",
        default=None,
    )
    group.add_argument(
        "--optout", type=str, help="Opt-out keyword. If set, projects with this keyword will be excluded", default=None
    )

    args = parser.parse_args()

    return args


def __connect_xnat(args: argparse.Namespace):
    """This function collects credentials and connects to XNAT

    Parameters
    ----------
    args : Namespace
        Namespace containing commandline arguments

    Returns
    -------
    XNATSession
    """
    if not (server := args.server):
        if not (server := os.environ.get(XNATPY_HOST_ENV)):
            if not (server := os.environ.get(XNAT_HOST_ENV)):
                raise RuntimeError("No server specified: no argument nor environment variable found")
    if not (username := args.username):
        if not (username := os.environ.get(XNAT_USER_ENV)):
            logger.info("No username set, using anonymous/netrc login")
    if not (password := args.password):
        if not (password := os.environ.get(XNAT_PASS_ENV)):
            logger.info("No password set, using anonymous/netrc login")

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
    run_cli_app()


# except Exception as e:
#     print(f"Error running xnatdcat:\n{e}")
#     exit(-1)


def run_cli_app():
    args = __parse_cli_args()
    log._add_file_handler(args.logfile)
    logger.info("======= XNATDCAT New Run ========")
    if args.verbose:
        log.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")

    config = load_configuration(args.config)

    if args.optin or args.optout:
        config['xnatdcat']['optin'] = args.optin
        config['xnatdcat']['optout'] = args.optout

    with __connect_xnat(args) as session:
        g = xnat_to_RDF(session, config)

    if args.output:
        g.serialize(destination=args.output, format=args.format)
    else:
        print(g.serialize(format=args.format))


if __name__ == "__main__":
    cli_main()
