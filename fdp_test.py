"""Simple test script to push stuff to a Fair Data Point"""

import argparse
import logging
import os
from pathlib import Path, PurePath
from typing import Dict

import click
import rdflib
from rdflib import FOAF, Graph, URIRef
from rdflib.namespace import DCAT, DCTERMS, RDF
from requests import HTTPError
from tqdm import tqdm
from xnat.session import XNATSession

from xnatdcat import log
from xnatdcat.cli_app import __connect_xnat, load_xnatdcat_configuration
from xnatdcat.const import VCARD
from xnatdcat.fdpclient import FDPClient, prepare_dataset_graph_for_fdp
from xnatdcat.xnat_parser import XNATParserError, _check_elligibility_project, xnat_list_datasets, xnat_to_DCATDataset

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
    parser.add_argument("--fdp", default=None, type=str, required=True, help="URL of FDP to push to")
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
    parser.add_argument("-V", "--version", action="version", version="%(prog)s 'fdp test'")

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


# @click.command()
# @click.argument('graph_file', required=True, type=click.File())
# @click.option("--fdp", default="https://health-ri.sandbox.semlab-leiden.nl", help="URI of FDP")
# @click.option("--username", required=True, help="Username / email of FDP")
# @click.option("--password", required=True, help="Password of FDP")
def fdp(fdp_uri, username, password, **kwargs):
    click.echo(f"Connecting to FDP: {fdp_uri}, username: {username}, password: { '*' * max(len(password), 8) })")
    try:
        fdpclient = FDPClient(fdp_uri, username, password)
    except HTTPError as e:
        click.echo(e.response.text)
        raise e

    return fdpclient


# @click.command("doei")
def graph(graph_file):
    graph = Graph().parse(graph_file)
    click.echo(f"G: {graph.serialize()}")


if __name__ == "__main__":
    args = __parse_cli_args()
    config = load_xnatdcat_configuration(args.config)
    logger.info("======= XNATDCAT FDP test New Run ========")
    if True:
        log.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")

    try:
        fdp_pass = os.environ["XNATDCAT_PASSWORD"]
        fdp_user = os.environ["XNATDCAT_USERNAME"]
    except KeyError:
        logger.error("Make sure the XNATDCAT_USERNAME and XNATDCAT_PASSWORD are set with FDP user/pass")

    fdpclient = fdp(args.fdp, fdp_user, fdp_pass)

    # Hardcoded, please forgive me.
    catalog_uri = URIRef("https://health-ri.sandbox.semlab-leiden.nl/catalog/e3faf7ad-050c-475f-8ce4-da7e2faa5cd0")

    with __connect_xnat(args.server, args.username, args.password) as session:
        xnat_to_FDP(session, config, catalog_uri, fdpclient)
