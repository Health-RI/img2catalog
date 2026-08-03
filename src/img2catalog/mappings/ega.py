import logging
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import AnyHttpUrl
from rdflib import URIRef
from sempyro import LiteralField
from sempyro.dcat import AccessRights
from sempyro.hri_dcat import DatasetStatus, DatasetTheme, HRIAgent, HRIDataset, HRIVCard

logger = logging.getLogger(__name__)

# Source used:
# https://healthri.sharepoint.com/:x:/r/sites/hri-team022/_layouts/15/Doc.aspx?sourcedoc=%7BE3EC5B3F-6BB2-404B-9DA9-489A90BAC077%7D&file=EGA%20Health-RI%20Core%20mapping.xlsx&action=default&mobileredirect=true

def get_identifier(ega_dataset: Dict) -> str:
    """Build the identifiers.org URI for an EGA dataset's accession_id."""
    return f"http://identifiers.org/ega.dataset:{ega_dataset['accession_id']}"

def get_title(ega_dataset: Dict) -> str:
    return ega_dataset["title"]

def get_description(ega_dataset: Dict) -> str:
    return ega_dataset["description"]

def get_number_of_records(ega_dataset: Dict) -> Optional[int]:
    return ega_dataset.get("num_samples")

def get_release_date(ega_dataset: Dict) -> Optional[datetime]:
    released_date = ega_dataset.get("released_date")
    if released_date is None:
        return None

    try:
        return datetime.fromisoformat(released_date)
    except ValueError:
        logger.warning("Could not parse EGA release date %r as ISO 8601, passing through as-is", released_date)
        return released_date

def get_keyword(ega_dataset: Dict) -> List[LiteralField]:
    """Map EGA's free-text `technologies` field to DCAT-AP keywords."""
    return [LiteralField(value=technology) for technology in ega_dataset.get("technologies", [])]

def map_ega_to_healthri_dcat_dataset(ega_dataset: Dict, config: Dict) -> HRIDataset:
    dataset_config = config["dataset"]
    publisher_config = dataset_config["publisher"]
    contact_point_config = dataset_config["contact_point"]

    dataset_themes = [DatasetTheme(URIRef(theme)) for theme in dataset_config["theme"]]

    dataset_keywords = get_keyword(ega_dataset)
    dataset_keywords.extend(LiteralField(value=keyword) for keyword in dataset_config.get("keyword", []))

    dataset_applicable_legislation = [AnyHttpUrl(url) for url in dataset_config["applicable_legislation"]]

    publisher_identifiers = [LiteralField(value=identifier) for identifier in publisher_config["identifier"]]

    publisher = HRIAgent(
        name=[LiteralField(value=name) for name in publisher_config["name"]],
        identifier=publisher_identifiers,
        mbox=publisher_config["mbox"],
        homepage=publisher_config["homepage"],
    )

    contact_point = HRIVCard(
        hasEmail=contact_point_config["email"],
        formatted_name=contact_point_config["formatted_name"],
    )

    dataset = HRIDataset(
        # Directly mapped from EGA
        identifier=LiteralField(value=get_identifier(ega_dataset)),
        title=[LiteralField(value=get_title(ega_dataset))],
        description=[LiteralField(value=get_description(ega_dataset))],
        release_date=get_release_date(ega_dataset),
        number_of_records=get_number_of_records(ega_dataset),
        keyword=dataset_keywords,
        # Not present in EGA metadata, supplied from local node configuration (see
        # docs/ega_mapping.md for the fields that are not (yet) mapped from EGA)
        publisher=publisher,
        contact_point=contact_point,
        creator=[publisher],
        theme=dataset_themes,
        applicable_legislation=dataset_applicable_legislation,
        access_rights=AccessRights(URIRef(dataset_config["access_rights"])),
    )

    return dataset