"""Simple tool to query an XNAT instance and serialize projects as datasets"""
import logging

from rdflib import DCAT, DCTERMS, FOAF, Graph, Namespace, URIRef
from rdflib.term import Literal
from tqdm import tqdm

from .dcat_model import DCATCatalog, DCATDataSet, VCard
from xnat.session import XNATSession
from typing import Dict

VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")

logger = logging.getLogger('xnatdcat')


def xnat_to_DCATDataset(project: XNATSession, config: Dict) -> DCATDataSet:
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


def xnat_to_DCATCatalog(session: XNATSession, config: Dict) -> DCATCatalog:
    """Creates a DCAT-AP compliant Catalog from XNAT instance

    Parameters
    ----------
    session : XNATSession
        An XNATSession of the XNAT instance that is going to be queried

    Returns
    -------
    DCATCatalog
        DCATCatalog object with fields filled in
    """
    catalog_uri = URIRef(session.url_for(session))
    catalog = DCATCatalog(
        uri=catalog_uri,
        title=Literal(config['catalog']['title']),
        description=Literal(config['catalog']['description']),
    )
    return catalog


def xnat_to_RDF(session: XNATSession, config: Dict) -> Graph:
    """Creates a DCAT-AP compliant Catalog of Datasets from XNAT

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

    # We can kinda assume session always starts with /data/archive, see xnatpy/xnat/session.py L988
    catalog = xnat_to_DCATCatalog(session, config)

    failure_counter = 0

    for p in tqdm(session.projects.values()):
        try:
            dcat_dataset = xnat_to_DCATDataset(p, config)
            d = dcat_dataset.to_graph(userinfo_format=VCARD.VCard)
            catalog.Dataset.append(dcat_dataset.uri)
        except ValueError as v:
            logger.info(f"Project {p.name} could not be converted into DCAT: {v}")
            failure_counter += 1
            continue
        export_graph += d

    export_graph += catalog.to_graph()

    if failure_counter > 0:
        logger.warning("There were %d projects with invalid data for DCAT generation", failure_counter)

    return export_graph
