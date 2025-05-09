import datetime
import html
import logging
import re
from typing import Dict, List, Union

from tqdm import tqdm
from xnat.core import XNATBaseObject
from xnat.session import XNATSession

from img2catalog.const import REMOVE_OPTIN_KEYWORD, INCLUDE_PRIVATE
from img2catalog.inputs.config import ConfigInput

logger = logging.getLogger(__name__)

class XNATInput:
    """ Input class that handles getting the metadata from XNAT

    Parameters
    ----------
    config : Dict
        Dictionary containing the contents of the configuration
    session : XNATSession
        Logged in session of the XNAT that you want to gather metadata from

    """

    def __init__(self, config: Dict, session: XNATSession):
        self.config = config
        self.session = session

    def get_and_update_metadata(self, config_input: ConfigInput) -> Dict[str, List[Dict]]:
        """Gathers metadata from XNAT and updates them using ConfigInput

        Parameters
        ----------
        config_input: ConfigInput:
             ConfigInput object

        Returns
        -------
        List[Dict]
            A list with dictionaries containing metadata per dataset
        """
        unmapped_objects = self.get_metadata()
        config_catalog = config_input.get_metadata_concept('catalog')
        config_dataset = config_input.get_metadata_concept('dataset')

        unmapped_objects = {
            'catalog': config_input.update_metadata(unmapped_objects['catalog'], config_catalog),
            'dataset': config_input.update_metadata(unmapped_objects['dataset'], config_dataset)
        }

        return unmapped_objects

    def get_metadata(self) -> Dict[str, List[Dict]]:
        """Gathers metadata from XNAT

        Returns
        -------
        List[Dict]
            A list with dictionaries containing metadata per dataset
        """
        xnat_catalogs = self.get_metadata_catalogs()
        xnat_datasets = self.get_metadata_datasets()

        xnat_catalogs[0]['dataset'] = [dataset['uri'] for dataset in xnat_datasets]

        unmapped_objects = {
            'catalog': xnat_catalogs,
            'dataset': xnat_datasets
        }
        return unmapped_objects

    def get_metadata_datasets(self) -> List[Dict]:
        """Gathers metadata for datasets from XNAT projects

        Returns
        -------
        List[Dict]
            A list with dictionaries containing metadata per dataset
        """

        failure_counter = 0
        dataset_list = []

        for p in tqdm(self.session.projects.values()):
            try:
                dcat_dataset = self.project_to_dataset(p)

            except XNATParserError as v:
                logger.info(f"Project {p.name} could not be converted into DCAT: {v}")

                if v.error_list:
                    for err in v.error_list:
                        logger.info(f"- {err}")
                failure_counter += 1
                continue

            if dcat_dataset:
                dataset_list.append(dcat_dataset)

        if failure_counter > 0:
            logger.warning("There were %d projects with invalid data for DCAT generation", failure_counter)

        return dataset_list

    def project_to_dataset(self, project: Union[XNATBaseObject, str]) -> Union[Dict, None]:
        """Gather Dataset metadata from an XNAT project

        Currently fills in the title, description and keywords. The first two are mandatory fields
        for a dataset in DCAT-AP, the latter is a bonus.

        Note: XNAT sees keywords as one string field, this function assumes they are comma-separated.

        Parameters
        ----------
        project : XNATBaseObject, str
            An XNat project instance, or its name, which is to be converted to a dataset

        Returns
        -------
        Union[Dict, None]
            A dictionary containing the metadata for the project, or None if the project is not eligible
        """
        if isinstance(project, str):
            project = self.session.projects[project]

        if not self._check_eligibility_project(project):
            logger.debug("Project %s not eligible, skipping", project.id)
            return None

        # Specification from XNAT:  Optional: Enter searchable keywords. Each word, separated by a space,
        # can be used independently as a search string.
        keywords = filter_keyword(split_keywords(project.keywords), self.config)

        error_list = []
        if not (project.pi.firstname or project.pi.lastname):
            error_list.append("Cannot have empty name of PI")
        if not project.description:
            error_list.append("Cannot have empty description")

        if error_list:
            raise XNATParserError("Errors encountered during the parsing of XNAT.", error_list=error_list)

        dataset_uri = project.external_uri()

        creator_list = [self._format_investigator(project.pi)]

        if project.investigators:
            for investigator in project.investigators:
                creator = self._format_investigator(investigator)
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

    def _format_investigator(self, investigator) -> Dict:
        creator = {
            'name': [f"{investigator.title or ''} {investigator.firstname} {investigator.lastname}".strip()],
            # 'identifier': "http://example.com",  # Should be ORCID?
        }
        return creator

    def get_metadata_catalogs(self) -> List[Dict]:
        """Gathers metadata for catalogs from the XNAT instance

        Returns
        -------
        List[Dict]
            A list with dictionaries containing metadata per catalog
        """
        catalog = {'uri': self.session.url_for(self.session), 'dataset': []}
        return [catalog]

    def _is_private_project(self, project) -> bool:
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

        return accessibility == "private".casefold()

    def _check_eligibility_project(self, project) -> bool:
        """Checks if a project is eligible for indexing given its properties and img2catalog config

        Parameters
        ----------
        project : XNAT Project
            The XNATpy project to be indexed

        Returns
        -------
        bool
            Returns True if the project could be indexed, False if not.
        """
        # Check if project is private. If it is, skip it
        if self._is_private_project(project) and not (
                self.config.get("img2catalog", INCLUDE_PRIVATE) and
                self.config["img2catalog"].get("include_private", INCLUDE_PRIVATE)):
            logger.debug("Project %s is private, not eligible", project.id)
            return False

        if not check_optin_optout(project, self.config):
            logger.debug("Skipping project %s due to keywords", project.id)
            return False

        logger.debug("Project %s is eligible for indexing", project)

        return True


class XNATParserError(ValueError):
    """Exception that can contain a list of errors from the XNAT parser.

    Parameters
    ----------
    message: str
        Exception message
    error_list: List[str]
        List of strings containing error messages. Default is None

    """

    def __init__(self, message: str, error_list: List[str] = None):
        super().__init__(message)
        self.error_list = error_list


def filter_keyword(keywords: Union[List[str], None], config: Dict) -> List[str]:
    """Filters the opt-in keyword from the keywords list

    If no opt-in keyword is set, all keywords will be returned.
    If remove_keywords is set to False, all keywords will be returned.
    If the opt-in keyword cannot be found, all keywords will be returned.

    Parameters
    ----------
    keywords : Union[List[str], None]
        List of keywords
    config : Dict
        img2catalog configuration dictionary

    Returns
    -------
    List[str]
        List of keywords, with the opt-in keyword filtered out if necessary
    """
    if config.get("img2catalog") and config["img2catalog"].get("remove_optin", REMOVE_OPTIN_KEYWORD):
        optin_kw = config["img2catalog"].get("optin")
        if optin_kw in keywords:
            keywords.remove(optin_kw)

    return keywords


def split_keywords(keywords: Union[str, None]) -> List[str]:
    """Takes a keyword list and splits it up into a list of keywords

    Removes all non alphanumeric characters from the keywords

    Parameters
    ----------
    keywords : str
        String containing all keywords. Space, comma or (semi-)colon-separated.

    Returns
    -------
    List[str]
        List of keywords, empty list if there are no keywords
    """
    keyword_list = []
    if keywords and len(keywords.strip()) > 0:
        keyword_list = [
            kw.strip()
            for kw in re.split(r"[\.,;: ]", keywords)
        ]


    # Filter out all empty strings, then return list
    return list(filter(None, keyword_list))


def check_optin_optout(project, config: Dict) -> bool:
    """This function checks if the project is eligible for indexing, given the opt-in/opt-out keywords

    Parameters
    ----------
    project
        XNAT project of which the eligibility needs to be determined
    config : Dict
        Configuration dictionary with the opt-in/opt-out keys

    Returns
    -------
    bool
        Returns True if a project is eligible for indexing, False if it is not.
    """
    try:
        optin_kw = config["img2catalog"].get("optin")
        optout_kw = config["img2catalog"].get("optout")
    except KeyError:
        # If key not found, means config is not set, so no opt-in/opt-out set so always eligible.
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
