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
from xnatdcat.fdpclient import FDPClient
from xnatdcat.xnat_parser import XNATParserError, _check_elligibility_project, xnat_to_DCATDataset

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


def remove_node_from_graph(node, graph: Graph):
    """Completely removes a node and all references to it from a graph

    Parameters
    ----------
    node : ...
        Node to be removed
    graph : Graph
        Graph to remove it from
    """
    # Remove all triples with the node as a subject and an object
    graph.remove((node, None, None))
    graph.remove((None, None, node))


# @click.command("doei")
def graph(graph_file):
    graph = Graph().parse(graph_file)
    click.echo(f"G: {graph.serialize()}")


def prepare_dataset_graph_for_fdp(dataset_graph: Graph, catalog_uri: URIRef):
    """Mangles the graph of a dataset in such a way a FDP can take it

    Adds the isPartOf property to point back to parent catalog and removes some blind VCard nodes
    that it doens't seem to like.

    Parameters
    ----------
    dataset_graph : Graph
        RDFlib graph of the DCAT Dataset
    catalog_uri : URIRef
        URIRef of the Catalog to point back to

    Raises
    ------
    TypeError
        if the catalog_uri is not a URIRef (e.g. it is a string)
    """
    if type(catalog_uri) is not URIRef:
        raise TypeError("catalog_uri is not a URIRef")

    # For each dataset, find the creator node. If it is a VCard, get rid of it.
    for dataset in dataset_graph.subjects(RDF.type, DCAT.Dataset):
        creator_node = dataset_graph.value(subject=dataset, predicate=DCTERMS.creator, any=False)
        if creator_node:
            if dataset_graph.value(subject=creator_node, predicate=RDF.type, any=False) == VCARD.VCard:
                remove_node_from_graph(creator_node, dataset_graph)

        contactpoint_node = dataset_graph.value(subject=dataset, predicate=DCAT.contactPoint, any=False)
        if contactpoint_node:
            if dataset_graph.value(subject=contactpoint_node, predicate=RDF.type, any=False) == VCARD.VCard:
                remove_node_from_graph(contactpoint_node, dataset_graph)

        # This is FDP specific: Dataset points back to the Catalog
        if not dataset_graph.value(subject=dataset, predicate=DCTERMS.isPartOf, any=False):
            dataset_graph.add((dataset, DCTERMS.isPartOf, catalog_uri))


def xnat_to_FDP(session: XNATSession, config: Dict, catalog_uri: URIRef, fdpclient: FDPClient) -> None:
    """Pushes DCAT-AP compliant Datasets to FDP

    Parameters
    ----------
    session : XNATSession
        An XNATSession of the XNAT instance that is going to be queried
    config : Dict
        A dictionary containing the configuration of xnatdcat

    Returns
    -------
    Graph
        An RDF graph containing DCAT-AP
    """
    export_graph = Graph()

    # To make output cleaner, bind these prefixes to namespaces
    export_graph.bind("dcat", DCAT)
    export_graph.bind("dcterms", DCTERMS)
    export_graph.bind("foaf", FOAF)
    export_graph.bind("vcard", VCARD)

    failure_counter = 0

    for project in tqdm(session.projects.values()):
        try:
            if not _check_elligibility_project(project, config):
                logger.debug("Project %s not elligible, skipping", project.id)

            dcat_dataset = xnat_to_DCATDataset(project, config)
            # Below is necessary for FDP
            dcat_dataset.is_part_of = catalog_uri

            dataset_graph = dcat_dataset.to_graph(userinfo_format=VCARD.VCard)

        except XNATParserError as v:
            logger.info(f"Project {project.name} could not be converted into DCAT: {v}")

            for err in v.error_list:
                logger.info(f"- {err}")
            failure_counter += 1
            continue

        prepare_dataset_graph_for_fdp(dataset_graph, catalog_uri)

        logger.debug("Going to push %s to FDP", project.id)
        fdpclient.create_and_publish("dataset", dataset_graph)

    if failure_counter > 0:
        logger.warning("There were %d projects with invalid data for DCAT generation", failure_counter)

    # return export_graph


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

    with __connect_xnat(args) as session:
        xnat_to_FDP(session, config, catalog_uri, fdpclient)
