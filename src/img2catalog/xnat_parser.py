"""Simple tool to query an XNAT instance and serialize projects as datasets"""

import logging
import re
from typing import Dict, List, Tuple, Union

from rdflib import DCAT, DCTERMS, FOAF, Graph, URIRef
from sempyro.dcat import DCATCatalog, DCATDataset
from sempyro.vcard import VCARD, VCard

from tqdm import tqdm
from xnat.core import XNATBaseObject
from xnat.session import XNATSession

from img2catalog.fdpclient import FDPClient, FDPSPARQLClient, add_or_update_dataset, prepare_dataset_graph_for_fdp

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


def xnat_to_DCATDataset(project: XNATBaseObject, config: Dict) -> Tuple[DCATDataset, URIRef]:
    """This function populates a DCAT Dataset class from an XNat project

    Currently fills in the title, description and keywords. The first two are mandatory fields
    for a dataset in DCAT-AP, the latter is a bonus.

    Note: XNAT sees keywords as one string field, this function assumes they are comma-separated.

    Parameters
    ----------
    project : XNatListing
        An XNat project instance which is to be generated
    config : Dict
        A dictionary containing the configuration of img2catalog

    Returns
    -------
    DCATDataset
        DCATDataset object with fields filled in
    URIRef
        Subject that could be used
    """
    # Specification from XNAT:  Optional: Enter searchable keywords. Each word, separated by a space,
    # can be used independently as a search string.
    keywords = split_keywords(project.keywords)

    error_list = []
    if not (project.pi.firstname or project.pi.lastname):
        error_list.append("Cannot have empty name of PI")
    if not project.description:
        error_list.append("Cannot have empty description")

    if error_list:
        raise XNATParserError("Errors encountered during the parsing of XNAT.", error_list=error_list)

    project_uri = project.external_uri()

    creator_vcard = [
        VCard(
            full_name=[f"{project.pi.title or ''} {project.pi.firstname} {project.pi.lastname}".strip()],
            hasUID=URIRef("http://example.com"),  # Should be ORCID?
        )
    ]

    dataset_dict = {
        "title": [project.name],
        "description": [project.description],
        "creator": creator_vcard,
        "keyword": keywords,
        "identifier": [project_uri],
    }

    contact_point_vcard = [contact_point_vcard_from_config(config)]
    if any(contact_point_vcard):
        dataset_dict["contact_point"] = contact_point_vcard

    project_dataset = DCATDataset(**dataset_dict)

    return project_dataset, URIRef(project_uri)


def xnat_to_DCATCatalog(session: XNATSession, config: Dict) -> DCATCatalog:
    """Creates a DCAT-AP compliant Catalog from XNAT instance

    Parameters
    ----------
    session : XNATSession
        An XNATSession of the XNAT instance that is going to be queried
    config : Dict
        A dictionary containing the configuration of img2catalog

    Returns
    -------
    DCATCatalog
        DCATCatalog object with fields populated
    """
    catalog = DCATCatalog(
        title=[config["catalog"]["title"]],
        description=[config["catalog"]["description"]],
    )
    return catalog


def xnat_to_RDF(session: XNATSession, config: Dict) -> Graph:
    """Creates a DCAT-AP compliant Catalog of Datasets from XNAT

    Parameters
    ----------
    session : XNATSession
        An XNATSession of the XNAT instance that is going to be queried
    config : Dict
        A dictionary containing the configuration of img2catalog

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

    catalog = xnat_to_DCATCatalog(session, config)
    catalog_uri = URIRef(session.url_for(session))

    dataset_list = xnat_list_datasets(session, config)

    # Assign an empty list so we can easily append datasets
    catalog.dataset = []

    for dcat_dataset, subject in dataset_list:
        d = dcat_dataset.to_graph(subject)
        export_graph += d
        catalog.dataset.append(subject)

    export_graph += catalog.to_graph(catalog_uri)

    return export_graph


def xnat_to_FDP(
    session: XNATSession, config: Dict, catalog_uri: URIRef, fdpclient: FDPClient, sparqlclient: FDPSPARQLClient = None
) -> None:
    """Pushes DCAT-AP compliant Datasets to FDP

    Parameters
    ----------
    session : XNATSession
        An XNATSession of the XNAT instance that is going to be queried
    config : Dict
        A dictionary containing the configuration of img2catalog
    catalog_uri : URIRef
        URI of the catalog in which the datasets will be placed
    fdpclient : FDPClient
        An instance of FDPClient of the FDP where the datasets will be put
    sparqlclient : FDPSPARQLClient, optional
        An instance of FDPSPARQLClient which can be used for updating existing datasts, by default None

    Returns
    -------
    Graph
        An RDF graph containing DCAT-AP
    """
    dataset_list = xnat_list_datasets(session, config)

    for dataset, subject in tqdm(dataset_list):
        dataset_graph = dataset.to_graph(subject)
        prepare_dataset_graph_for_fdp(dataset_graph, catalog_uri)
        logger.debug("Going to push %s to FDP", dataset.title)
        try:
            add_or_update_dataset(dataset_graph, fdpclient, dataset.identifier[0], catalog_uri, sparqlclient)
        except Exception as e:
            logger.warn("Error pushing dataset to FDP: %s", e)


def xnat_list_datasets(session: XNATSession, config: Dict) -> List[DCATDataset]:
    """Acquires a list of elligible XNAT datasets

    Parameters
    ----------
    session : XNATSession
        An XNATSession of the XNAT instance that is going to be queried
    config : Dict
        A dictionary containing the configuration of img2catalog

    Returns
    -------
    List[DCATDataset, URI]
        List of DCAT models of elligible datasets, along with their URIs (for subjects)

    """
    failure_counter = 0
    dataset_list = []

    for p in tqdm(session.projects.values()):
        try:
            if not _check_elligibility_project(p, config):
                logger.debug("Project %s not elligible, skipping", p.id)
                continue

            dcat_dataset = xnat_to_DCATDataset(p, config)
            dataset_list.append(dcat_dataset)

        except XNATParserError as v:
            logger.info(f"Project {p.name} could not be converted into DCAT: {v}")

            for err in v.error_list:
                logger.info(f"- {err}")
            failure_counter += 1
            continue

    if failure_counter > 0:
        logger.warning("There were %d projects with invalid data for DCAT generation", failure_counter)

    return dataset_list


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
                for kw in re.split(r"[\.,;: ]", xnat_keywords)
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
    accessibility = project.xnat_session.get(f"{project.uri}/accessibility").text.casefold()
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
        optin_kw = config["img2catalog"].get("optin")
        optout_kw = config["img2catalog"].get("optout")
    except KeyError:
        # If key not found, means config is not set, so no opt-in/opt-out set so always elligible.
        return True

    if optin_kw:
        if optin_kw not in split_keywords(project.keywords):
            logger.debug("Project %s does not contain keyword on opt-in list, skipping", project)
            return False
    elif optout_kw:
        if optout_kw in split_keywords(project.keywords):
            logger.debug("Project %s contains keyword on opt-out list, skipping", project)
            return False

    return True


def _check_elligibility_project(project, config: Dict) -> bool:
    """Checks if a project is elligible for indexing given its properties and img2catalog config

    Parameters
    ----------
    p : XNAT Project
        The XNATpy project to be index4ed
    config : Dict
        Dictionary containing img2catalog config

    Returns
    -------
    bool
        Returns True if the project could be indexed, False if not.
    """
    # Check if project is private. If it is, skip it
    if xnat_private_project(project):
        logger.debug("Project %s is private, not elligible", project.id)
        return False

    if not _check_optin_optout(project, config):
        logger.debug("Skipping project %s due to keywords", project.id)
        return False

    logger.debug("Project %s is elligible for indexing", project)

    return True


def contact_point_vcard_from_config(config: Dict) -> Union[VCard, None]:
    """Generates a VCard for contact_point of datasets

    Parameters
    ----------
    config : Dict
        img2catalog configuration

    Returns
    -------
    Union[VCARD, None]
        VCard if info is present in configuration, None if not.
    """
    try:
        contact_config = config["dataset"]["contact_point"]
    except KeyError:
        return None

    # email should be URIRef (but not path, https://stackoverflow.com/a/27151227)
    contact_email = contact_config.get("email")
    if contact_email:
        if not contact_email.startswith("mailto:"):
            contact_email = f"mailto:{contact_email}"
        contact_email = URIRef(contact_email)

    contact_vcard = VCard(
        full_name=[contact_config["full_name"]], hasEmail=[contact_email], hasUID=URIRef("http://example.com")
    )

    return contact_vcard
