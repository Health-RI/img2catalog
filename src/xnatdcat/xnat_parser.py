"""Simple tool to query an XNAT instance and serialize projects as datasets"""
import logging
import re

from rdflib import DCAT, DCTERMS, FOAF, Graph, Namespace, URIRef
from rdflib.term import Literal
from tqdm import tqdm

from .dcat_model import DCATCatalog, DCATDataSet, VCard
from xnat.session import XNATSession
from typing import Dict, List, Union

from .const import VCARD

logger = logging.getLogger(__name__)


class XNATParserError(ValueError):
    """Exception that can contain an list of errors from the XNAT parser.

    Parameters
    ----------
    message: str
        Exception message
    error_list: list
        List of strings containing error messages. Default is None

    """

    def __init__(self, message: str, error_list: List[str] = None):
        super().__init__(message)
        self.error_list = error_list


def xnat_to_DCATDataset(project: XNATSession, config: Dict) -> DCATDataSet:
    """This function populates a DCAT Dataset class from an XNat project

    Currently fills in the title, description and keywords. The first two are mandatory fields
    for a dataset in DCAT-AP, the latter is a bonus.

    Note: XNAT sees keywords as one string field, this function assumes they are comma-separated.

    Parameters
    ----------
    project : XNatListing
        An XNat project instance which is to be generated
    config : Dict
        A dictionary containing the configuration of xnatdcat

    Returns
    -------
    DCATDataSet
        DCATDataSet object with fields filled in
    """
    # Specification from XNAT:  Optional: Enter searchable keywords. Each word, separated by a space,
    # can be used independently as a search string.
    keywords = [Literal(kw) for kw in split_keywords(project.keywords)]

    error_list = []
    if not (project.pi.firstname or project.pi.lastname):
        error_list.append("Cannot have empty name of PI")
    if not project.description:
        error_list.append("Cannot have empty description")

    if error_list:
        raise XNATParserError("Errors encountered during the parsing of XNAT.", error_list=error_list)

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
    config : Dict
        A dictionary containing the configuration of xnatdcat

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

    # We can kinda assume session always starts with /data/archive, see xnatpy/xnat/session.py L988
    catalog = xnat_to_DCATCatalog(session, config)

    failure_counter = 0

    for p in tqdm(session.projects.values()):
        try:
            # Check if project is private. If it is, skip it
            if xnat_private_project(p):
                logger.debug("Project %s is private, skipping", p.id)
                continue

            logger.debug("Going to process project %s", p)

            if not _check_optin_optout(p, config):
                logger.debug("Skipping project %s due to keywords", p.id)
                continue

            dcat_dataset = xnat_to_DCATDataset(p, config)

            d = dcat_dataset.to_graph(userinfo_format=VCARD.VCard)
            catalog.Dataset.append(dcat_dataset.uri)
        except XNATParserError as v:
            logger.info(f"Project {p.name} could not be converted into DCAT: {v}")

            for err in v.error_list:
                logger.info(f"- {err}")
            failure_counter += 1
            continue

        export_graph += d

    export_graph += catalog.to_graph()

    if failure_counter > 0:
        logger.warning("There were %d projects with invalid data for DCAT generation", failure_counter)

    return export_graph


def split_keywords(xnat_keywords: Union[str, None]) -> List[str]:
    """Takes an XNAT keyword list and splits it up into a list of keywords

    Removes all non alphanumeric characters from the keywords

    Parameters
    ----------
    xnat_keywords : str
        String containing all keywords. Space, comma or (semi-)colon-separated.

    Returns
    -------
    List[str]
        List of keywords, empty list if there are no keywords
    """
    keyword_list = []
    if xnat_keywords:
        if len(xnat_keywords.strip()) > 0:
            keyword_list = [
                kw.strip()
                for kw in re.split("[\.,;: ]", xnat_keywords)
                # for kw in xnat_keywords.strip().replace(".", " ").replace(",", " ").replace(";", " ").split(" ")
            ]

    # Filter out all empty strings, then return list
    return list(filter(None, keyword_list))


def xnat_private_project(project) -> bool:
    """This function checks if an XNAT project is a private project

    Parameters
    ----------
    project : XNAT ProjectData
        The project of which the permission status needs to be investigated

    Returns
    --------
    bool
        Returns True if the project is private, False if it is protected or public

    Raises
    ------
    XNATParserError
        If the XNAT API returns an unknown value for accessibility
    """
    # The API URI is documented as part of the XNAT Project Attributes API at
    # https://wiki.xnat.org/xnat-api/project-attributes-api
    # As it is not exposed as part of the XNAT XSD, XNATPy does not generate a field for it

    # The API documentation says it should be Title case, in practice XNAT returns lowercase
    # Therefore I consider the case to be unreliable
    accessibility = project.xnat_session.get(f'{project.uri}/accessibility').text.casefold()
    known_accesibilities = ["public", "private", "protected"]
    if accessibility.casefold() not in known_accesibilities:
        raise XNATParserError(f"Unknown permissions of XNAT project: accessibility is '{accessibility}'")

    if accessibility == "private".casefold():
        return True
    else:
        return False


def _check_optin_optout(project, config: Dict) -> bool:
    """This function checks if the project is elligible for indexing, given the opt-in/opt-out keywords

    Parameters
    ----------
    project : XNAT
        XNAT project of which the elligiblity needs to be determined
    config : Dict
        Configuration dictionary with the opt-in/opt-out keys

    Returns
    -------
    bool
        Returns True if a project is elligible for indexing, False if it is not.
    """
    try:
        optin_kw = config['xnatdcat'].get('optin')
        optout_kw = config['xnatdcat'].get('optout')
    except KeyError:
        # If key not found, means config is not set, so no opt-in/opt-out set so always elligible.
        return True

    if optin_kw:
        if not optin_kw in split_keywords(project.keywords):
            logger.debug("Project %s does not contain keyword on opt-in list, skipping", project)
            return False
    elif optout_kw:
        if optout_kw in split_keywords(project.keywords):
            logger.debug("Project %s contains keyword on opt-out list, skipping", project)
            return False

    return True
