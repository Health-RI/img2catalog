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
                full_name=Literal(f"{project.pi.title} {project.pi.firstname} {project.pi.lastname}".strip()),
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

    graphs = [xnat_to_DCATDataset(p).to_graph() for p in tqdm(session.projects.values())]
    for d in graphs:
        export_graph += d

    return export_graph
