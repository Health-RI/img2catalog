import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from pydantic import AnyHttpUrl
from rdflib import URIRef
from sempyro import LiteralField
from sempyro.dcat import AccessRights, Attribution
from sempyro.foaf import Agent
from sempyro.hri_dcat import DatasetStatus, DatasetTheme, HRIAgent, HRIDataset, HRIVCard

logger = logging.getLogger(__name__)

# Source used: Health-RI FSD "Mapping from the European Genome-Phenome Archive (EGA)" (schema v2.0.3)

EGA_DATASET_URL = "https://ega-archive.org/datasets/"
EGA_DAC_URL = "https://ega-archive.org/dacs/"


def _to_urls(values: List[str]) -> List[AnyHttpUrl]:
    return [AnyHttpUrl(value) for value in values]


def _optional(dataset_config: Dict, key: str, convert: Callable[[Any], Any]) -> Any:
    """Convert an optional config value, or return None when the key is absent."""
    if key not in dataset_config:
        return None
    return convert(dataset_config[key])


def get_identifier(ega_dataset: Dict) -> str:
    """Build the EGA archive URL for an EGA dataset's accession_id."""
    return f"{EGA_DATASET_URL}{ega_dataset['accession_id']}"


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
        logger.error("Could not parse EGA release date %r", released_date)
        return released_date


def get_keyword(ega_dataset: Dict) -> List[LiteralField]:
    """Map EGA's free-text `technologies` field to DCAT-AP keywords."""
    return [LiteralField(value=technology) for technology in ega_dataset.get("technologies", [])]


def get_contact_page(ega_dataset: Dict) -> List[str]:
    """Build the EGA archive URLs of the Data Access Committees (DACs) controlling the dataset."""
    return [f"{EGA_DAC_URL}{dac['accession_id']}" for dac in ega_dataset.get("dacs", [])]


def get_qualified_attribution(ega_dataset: Dict, dataset_config: Dict) -> List[Attribution]:
    """Attribute the dataset to the main contact(s) of its Data Access Committees (DACs).

    EGA does not provide an ORCID for DAC contacts, so the DAC page is used as the agent's identifier.
    The role is not present in EGA metadata and is taken from the local node configuration when set.
    """
    attribution_kwargs = {}
    role = dataset_config.get("qualified_attribution", {}).get("role")
    if role:
        attribution_kwargs["role"] = role

    attributions = []
    for dac in ega_dataset.get("dacs", []):
        for contact in dac.get("contacts") or []:
            if not contact.get("is_main"):
                continue

            agent_kwargs = {}
            if contact.get("email"):
                agent_kwargs["mbox"] = [f"mailto:{contact['email']}"]

            agent = Agent(
                name=[LiteralField(value=f"{contact.get('first_name', '')} {contact.get('surname', '')}".strip())],
                identifier=LiteralField(value=f"{EGA_DAC_URL}{dac['accession_id']}"),
                **agent_kwargs,
            )
            attributions.append(Attribution(agent=agent, **attribution_kwargs))

    return attributions


def map_ega_to_healthri_dcat_dataset(ega_dataset: Dict, config: Dict) -> HRIDataset:
    dataset_config = config["dataset"]
    publisher_config = dataset_config["publisher"]
    contact_point_config = dataset_config["contact_point"]

    dataset_themes = [DatasetTheme(URIRef(theme)) for theme in dataset_config["theme"]]

    dataset_keywords = get_keyword(ega_dataset)
    dataset_keywords.extend(LiteralField(value=keyword) for keyword in dataset_config.get("keyword", []))

    dataset_applicable_legislation = _to_urls(dataset_config["applicable_legislation"])

    publisher_identifiers = [LiteralField(value=identifier) for identifier in publisher_config["identifier"]]

    publisher_kwargs = {}
    if "publisher_type" in publisher_config:
        publisher_kwargs["publisher_type"] = publisher_config["publisher_type"]

    publisher = HRIAgent(
        name=[LiteralField(value=name) for name in publisher_config["name"]],
        identifier=publisher_identifiers,
        mbox=publisher_config["mbox"],
        homepage=publisher_config["homepage"],
        **publisher_kwargs,
    )

    contact_point_kwargs = {}
    contact_page = get_contact_page(ega_dataset)
    if contact_page:
        contact_point_kwargs["contact_page"] = contact_page

    contact_point = HRIVCard(
        hasEmail=contact_point_config["email"],
        formatted_name=contact_point_config["formatted_name"],
        **contact_point_kwargs,
    )

    # Properties in the order of the FSD mapping document. Values not present in EGA metadata are
    # supplied from the local node configuration; optional ones are left out when not configured.
    dataset_fields = {
        "access_rights": AccessRights(URIRef(dataset_config["access_rights"])),
        "applicable_legislation": dataset_applicable_legislation,
        "code_values": _optional(dataset_config, "code_values", _to_urls),
        # Contact point combines the DAC from EGA with contact details from the local node configuration
        "contact_point": contact_point,
        "creator": [publisher],
        "description": [LiteralField(value=get_description(ega_dataset))],
        "geographical_coverage": _optional(dataset_config, "spatial", _to_urls),
        "health_theme": _optional(dataset_config, "health_theme", _to_urls),
        "identifier": LiteralField(value=get_identifier(ega_dataset)),
        "is_referenced_by": _optional(dataset_config, "is_referenced_by", _to_urls),
        "keyword": dataset_keywords,
        "language": _optional(dataset_config, "language", _to_urls),
        "legal_basis": _optional(dataset_config, "legal_basis", _to_urls),
        "minimum_typical_age": _optional(dataset_config, "minimum_typical_age", int),
        "number_of_records": get_number_of_records(ega_dataset),
        "number_of_unique_individuals": _optional(dataset_config, "number_of_unique_individuals", int),
        "personal_data": _optional(dataset_config, "personal_data", _to_urls),
        "population_coverage": _optional(
            dataset_config, "population_coverage", lambda value: LiteralField(value=value)
        ),
        "publisher": publisher,
        "purpose": _optional(dataset_config, "purpose", _to_urls),
        "qualified_attribution": get_qualified_attribution(ega_dataset, dataset_config) or None,
        "release_date": get_release_date(ega_dataset),
        "status": _optional(dataset_config, "status", lambda value: DatasetStatus(URIRef(value))),
        "theme": dataset_themes,
        "title": [LiteralField(value=get_title(ega_dataset))],
        "type": _optional(dataset_config, "type", _to_urls),
    }

    return HRIDataset(**{field: value for field, value in dataset_fields.items() if value is not None})
