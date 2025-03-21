import datetime
import html
import logging
import re
from typing import Dict, List, Tuple, Union

from fairclient.fdpclient import FDPClient
from fairclient.sparqlclient import FDPSPARQLClient
from fairclient.utils import add_or_update_dataset
from rdflib import DCAT, DCTERMS, FOAF, Graph, URIRef
from sempyro.foaf import Agent
from sempyro.hri_dcat.hri_catalog import HRICatalog
from sempyro.hri_dcat.hri_dataset import HRIDataset
from sempyro.vcard import VCARD, VCard
from tqdm import tqdm
from xnat.core import XNATBaseObject
from xnat.session import XNATSession

from img2catalog.const import REMOVE_OPTIN_KEYWORD

logger = logging.getLogger(__name__)

class XNATInput:
    def __init__(self, config, session):
        self.config = config
        self.session = session

    def get_metadata_datasets(self):
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

        dataset_list = self.list_datasets()

        return dataset_list

    def list_datasets(self) -> List[HRIDataset]:
        """Acquires a list of elligible XNAT datasets

        Parameters
        ----------
        session : XNATSession
            An XNATSession of the XNAT instance that is going to be queried
        config : Dict
            A dictionary containing the configuration of img2catalog

        Returns
        -------
        List[HRIDataset]
            List of DCAT models of elligible datasets

        """
        failure_counter = 0
        dataset_list = []

        for p in tqdm(self.session.projects.values()):
            try:
                if not _check_elligibility_project(p, self.config):
                    logger.debug("Project %s not elligible, skipping", p.id)
                    continue

                dcat_dataset = xnat_to_DCATDataset(p, self.config)
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

    def get_metadata_catalogs(self):
        catalog = {
            'uri': self.session.url_for(self.session),
            'dataset': list()
        }
        return [catalog]


class XNATParserError(ValueError):
    """Exception that can contain a list of errors from the XNAT parser.

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


def xnat_to_DCATDataset(project: XNATBaseObject, config: Dict) -> Tuple[HRIDataset, URIRef]:
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
    HRIDataset
        HRIDataset object with fields filled in
    URIRef
        Subject that could be used
    """
    # Specification from XNAT:  Optional: Enter searchable keywords. Each word, separated by a space,
    # can be used independently as a search string.
    keywords = filter_keyword(split_keywords(project.keywords), config)

    error_list = []
    if not (project.pi.firstname or project.pi.lastname):
        error_list.append("Cannot have empty name of PI")
    if not project.description:
        error_list.append("Cannot have empty description")

    if error_list:
        raise XNATParserError("Errors encountered during the parsing of XNAT.", error_list=error_list)

    dataset_uri = project.external_uri()

    creator_list = list([xnat_investigator_to_Agent(project.pi)])

    if project.investigators:
        for investigator in project.investigators:
            creator = xnat_investigator_to_Agent(investigator)
            creator_list.append(creator)

    # TODO These are stub values, should be modified to reflect something slightly more accurate
    issued = datetime.datetime.now()
    modified = datetime.datetime.now()

    project_description = html.unescape(project.description)

    dataset_dict = {
        "title": [project.name],
        "description": [project_description],
        "creator": creator_list,
        "keyword": keywords,
        "identifier": dataset_uri,
        "issued": issued,
        "modified": modified,
        'uri': dataset_uri
    }

    return dataset_dict


def xnat_investigator_to_Agent(investigator) -> Agent:
    # creator_foaf = Agent(
    #     name=[f"{investigator.title or ''} {investigator.firstname} {investigator.lastname}".strip()],
    #     identifier="http://example.com",  # Should be ORCID?
    # )
    creator_foaf = {
        'name':[f"{investigator.title or ''} {investigator.firstname} {investigator.lastname}".strip()],
        'identifier':"http://example.com",  # Should be ORCID?
    }

    return creator_foaf


def filter_keyword(xnat_keywords: Union[List[str], None], config: Dict) -> List[str]:
    """Filters the opt-in keyword from the xnat keywords list

    If no opt-in keyword is set, all keywords will be returned.
    If remove_keywords is set to False, all keywords will be returned.
    If the opt-in keyword cannot be found, all keywords will be returned.

    Parameters
    ----------
    xnat_keywords : Union[List[str], None]
        List of XNAT keywords
    config : Dict
        img2catalog configuration dictionary

    Returns
    -------
    List[str]
        List of XNAT keywords, with the opt-in keyword filtered out if necessary
    """
    if config["img2catalog"].get("remove_optin", REMOVE_OPTIN_KEYWORD):
        optin_kw = config["img2catalog"].get("optin")
        if optin_kw in xnat_keywords:
            xnat_keywords.remove(optin_kw)

    # try:
    # except KeyError:
    #     # If key not found, means config is not set, so no opt-in/opt-out set so all are included
    #     return xnat_keywords

    # remove_keyword = config["img2catalog"].get("remove_optin", REMOVE_OPTIN_KEYWORD)

    # if remove_keyword:
    #     if optin_kw in xnat_keywords:
    #         return xnat_keywords

    return xnat_keywords


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


# def contact_point_vcard_from_config(config: Dict) -> Union[VCard, None]:
#     """Generates a VCard for contact_point of datasets
#
#     Parameters
#     ----------
#     config : Dict
#         img2catalog configuration
#
#     Returns
#     -------
#     Union[VCARD, None]
#         VCard if info is present in configuration, None if not.
#     """
#     try:
#         contact_config = config["dataset"]["contact_point"]
#     except KeyError:
#         return None
#
#     # email should be URIRef (but not path, https://stackoverflow.com/a/27151227)
#     contact_email = contact_config.get("email")
#     if contact_email:
#         if not contact_email.startswith("mailto:"):
#             contact_email = f"mailto:{contact_email}"
#         contact_email = URIRef(contact_email)
#
#         contact_vcard = VCard(
#             full_name=[contact_config["full_name"]], hasEmail=[contact_email], hasUID=URIRef("http://example.com")
#         )
#
#         return contact_vcard
#     else:
#         return None
