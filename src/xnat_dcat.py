"""Simple tool to query an XNAT instance and serialize projects as datasets"""
import argparse
from pathlib import PurePath
from sys import stderr

import xnat
from rdflib import DCAT, DCTERMS, FOAF, Graph, Namespace, URIRef
from rdflib.term import Literal
from tqdm import tqdm

from .dcat_model import DCATDataSet, VCard

VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")


def xnat_to_DCATDataset(project) -> DCATDataSet:
    """This function populates a DCAT Dataset class from an XNat project

    Currently fills in the title, description and keywords. The first two are mandatory fields
    for a dataset in DCAT-AP, the latter is a bonus.

    Note: XNAT sees keywords as one string field, this function assumes they are comma-separated.

    Parameters
    ----------
    project : XNatListing
        An XNat project instance which is to be generated

    Returns
    -------
    DCATDataSet
        DCATDataSet object with fields filled in
    """
    # First check if keywords field is not blank
    if xnat_keywords := project.keywords:
        keywords = [Literal(kw.strip()) for kw in xnat_keywords.split(",")]
    else:
        keywords = None

    project_dataset = DCATDataSet(
        uri=URIRef(project.external_uri()),
        title=[Literal(project.name)],
        description=Literal(project.description),
        creator=[
            VCard(
                full_name=Literal(
                    f"{project.pi.title} {project.pi.firstname} {project.pi.lastname}"
                    .strip()
                ),
                uid=URIRef("http://example.com"),  # Should be ORCID?
            )
        ],
        keyword=keywords,
    )

    return project_dataset


def XNAT_to_DCAT(session) -> Graph:
    """Creates a DCAT-AP compliant Catalog of Datasets from XNAT

    Note: Catalog itself not generated yet

    Parameters
    ----------
    session : XNATSession
        An XNATSession of the XNAT instance that is going to be queried

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

    graphs = [
        xnat_to_DCATDataset(p).to_graph() for p in tqdm(session.projects.values())
    ]
    for d in graphs:
        export_graph += d

    return export_graph


def __parse_cli_args():
    """Simple argument parser for commandline args"""
    parser = argparse.ArgumentParser(
        prog="XNAT to DCAT", description="This tool generates DCAT from XNAT"
    )
    parser.add_argument(
        "server",
        type=str,
        help="URI of the server to connect to (including http:// or https://)",
    )
    parser.add_argument(
        "-u",
        "--username",
        default=None,
        type=str,
        help="Username to use, leave empty to use netrc entry or anonymous login.",
    )
    parser.add_argument(
        "-p",
        "--password",
        default=None,
        type=str,
        help=(
            "Password to use with the username, leave empty when using netrc. If a"
            " username is given and no password, there will be a prompt on the console"
            " requesting the password."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        type=PurePath,
        help=(
            "Destination file to write output to. If not set, the script will print"
            " serialized output to stdout."
        ),
    )
    parser.add_argument(
        "-f",
        "--format",
        default="turtle",
        type=str,
        help=(
            "The format that the output should be written in. This value references a"
            " Serializer plugin in RDFlib. Supportd values are: "
            ' "xml", "n3", "turtle", "nt", "pretty-xml", "trix", "trig", "nquads",'
            ' "json-ld" and "hext". Defaults to "turtle".'
        ),
    )

    args = parser.parse_args()

    return args


def __connect_xnat(args):
    """Very simple function to connect to XNat and get a session"""
    session = xnat.connect(
        server=args.server, user=args.username, password=args.password
    )

    return session


def _cli_main():
    args = __parse_cli_args()

    session = __connect_xnat(args)
    g = XNAT_to_DCAT(session)

    if args.output:
        g.serialize(destination=args.output, format=args.format)
    else:
        print(g.serialize(format=args.format))


if __name__ == "__main__":
    _cli_main()
