from datetime import datetime
from typing import Dict

from pandas import Series
from pydantic import AnyHttpUrl
from rdflib import URIRef
from sempyro import LiteralField
from sempyro.dcat import AccessRights
from sempyro.time import PeriodOfTime

from sempyro.hri_dcat import HRIAgent, HRIVCard, HRIDataset, DatasetTheme

def format_temporal_coverage(temporal_coverage: str) -> PeriodOfTime:
    """Format 'DD-MM-YYYY to DD-MM-YYYY' into a PeriodOfTime object."""
    start_str, end_str = temporal_coverage.split("to")

    date_fmt = "%d-%m-%Y"
    start_date = datetime.strptime(start_str.strip(), date_fmt)
    end_date = datetime.strptime(end_str.strip(), date_fmt)

    return PeriodOfTime(
        start_date=LiteralField(value=start_date.strftime(date_fmt)),
        end_date=LiteralField(value=end_date.strftime(date_fmt))
    )

def format_date(start_date: str, end_date: str):
    # Get year from full start and end date
    year_start = start_date.split("-")[-1]
    year_end = end_date.split("-")[-1]

    # Date formatting logic
    if year_start == year_end: # e.g: 01-01-2025 == 31-12-2025 -> return 2025
        return year_start
    else:
        return f"{start_date}/{end_date}"  # e.g: 01-01-2024 and 31-12-2025 -> return 01-01-2024/01-12-2025


def format_title(data) -> str:
    """Format dataset title with instituteName, modality, start- and end date."""
    try:
        modality = data["modality"]
        institute = data["instituteName"]
        period = format_temporal_coverage(data["temporalCoverage"])
        start, end = period.start_date.value, period.end_date.value
        formatted_date_range = format_date(start, end)

    except KeyError as e:
        raise KeyError(f"Missing required field in data: {e}")

    return f"{institute} - {modality} - {formatted_date_range}"


def map_xds_to_healthri_dcat_dataset(row: Series, config: Dict) -> HRIDataset:
    dataset_config = config.get("dataset")
    publisher_config = dataset_config["publisher"]
    contact_point_config = dataset_config["contact_point"]
    dataset_formatted_title = format_title(row)

    dataset_themes = [
        DatasetTheme(URIRef(theme)) for theme in dataset_config["theme"]
    ]

    dataset_keywords = [
        LiteralField(value=keyword) for keyword in dataset_config["keyword"]
    ]

    dataset_applicable_legislation = [
        AnyHttpUrl(url) for url in dataset_config["applicable_legislation"]
    ]

    publisher_identifiers = [
        LiteralField(value=identifier) for identifier in publisher_config["identifier"]
    ]

    # Initialize Health-RI Models
    publisher = HRIAgent(
        name=[LiteralField(value=row["instituteName"])],
        identifier=publisher_identifiers,
        mbox = publisher_config["mbox"],
        homepage = publisher_config["homepage"],
    )

    contact_point = HRIVCard(
        hasEmail = contact_point_config["email"],
        formatted_name = contact_point_config["formatted_name"],
    )

    dataset = HRIDataset(
        # MANDATORY DCAT FIELDS
        identifier = LiteralField(value=dataset_config["identifier"]),
        title=[LiteralField(value=dataset_formatted_title)],
        description=[LiteralField(value=dataset_config["description"])],
        publisher = publisher,
        contact_point = contact_point,
        theme = dataset_themes,
        keyword= dataset_keywords,
        access_rights = AccessRights(URIRef(dataset_config["access_rights"])),
        creator = [publisher],
        applicable_legislation= dataset_applicable_legislation,

        # CSV FIELDS
        number_of_unique_individuals = int(row['numberOfUniqueIndividuals']),
        number_of_records = int(row['numberOfRecords']),
        minimum_typical_age = int(row['minTypicalAge']),
        maximum_typical_age = int(row['maxTypicalAge']),
    )

    return dataset