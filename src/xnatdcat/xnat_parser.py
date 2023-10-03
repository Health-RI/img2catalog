"""Simple tool to query an XNAT instance and serialize projects as datasets"""
from rdflib import DCAT, DCTERMS, FOAF, Graph, Namespace, URIRef
from rdflib.term import Literal
from tqdm import tqdm
import logging

from .dcat_model import DCATDataSet, VCard

VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")

logger = logging.getLogger(__name__)


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
    # Specification from XNAT:  Optional: Enter searchable keywords. Each word, separated by a space,
    # can be used independently as a search string.
    keywords = None
    if xnat_keywords := project.keywords:
        keywords = [Literal(kw.strip()) for kw in xnat_keywords.split(" ")]

    if not (project.pi.firstname or project.pi.lastname):
        raise ValueError("Cannot have empty name of PI")
    if not project.description:
        raise ValueError("Cannot have empty description")

    creator_vcard = [
        VCard(
            full_name=Literal(f"{project.pi.title or ''} {project.pi.firstname} {project.pi.lastname}".strip()),
            uid=URIRef("http://example.com"),  # Should be ORCID?
        )
    ]

    project_dataset = DCATDataSet(
        uri=URIRef(project.external_uri()),
        title=[Literal(project.name)],
        description=Literal(project.description),
        creator=creator_vcard,
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

    failure_counter = 0

    for p in tqdm(session.projects.values()):
        try:
            d = xnat_to_DCATDataset(p).to_graph(userinfo_format=VCARD.VCard)
        except ValueError as v:
            logger.info(f"Project {p.name} could not be converted into DCAT: {v}")
            failure_counter += 1
            continue
        export_graph += d

    if failure_counter > 0:
        logger.warning("There were %d projects with invalid data for DCAT generation", failure_counter)

    return export_graph
