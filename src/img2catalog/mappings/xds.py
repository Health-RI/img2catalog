from datetime import datetime
from pathlib import Path
from typing import Dict

from pandas import Series
from pydantic import AnyHttpUrl
from rdflib import URIRef
from sempyro import LiteralField
from sempyro.dcat import AccessRights
from sempyro.time import PeriodOfTime

from img2catalog.configmanager import load_img2catalog_configuration
from sempyro.hri_dcat import HRIAgent, HRIVCard, HRIDataset, DatasetTheme

from img2catalog.inputs.csv_reader import read_csv

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

def format_title(data) -> str:
    """ Format dataset title with instituteName, modality, start- and end date requirements."""
    try:
        modality = data["modality"]
        institute = data["instituteName"]
        period = format_temporal_coverage(data["temporalCoverage"])
    except KeyError as e:
        raise KeyError(f"Missing required field in data: {e}")

    start, end = period.start_date.value, period.end_date.value
    formatted_date = f"{start}/{end}" if start != end else start


    return f"{institute} - {modality} - {formatted_date}"

def map_xds_to_healthri_dcat_dataset(row: Series, config: Dict) -> HRIDataset:
    dataset_config = config.get("dataset")
    publisher_config = config.get("dataset")["publisher"]
    contact_point_config = config.get("dataset")["contact_point"]

    # Format dataset attributes
    dataset_formatted_title = format_title(row)

    # themes expect DatasetTheme
    dataset_themes = [
        DatasetTheme(URIRef(theme)) for theme in dataset_config["theme"]
    ]

    #  Map each keyword string to a LiteralField object
    dataset_keywords = [
        LiteralField(value=keyword) for keyword in dataset_config["keyword"]
    ]

    # applicable_legislation expects a list of AnyHttpUrl
    dataset_applicable_legislation = [
        AnyHttpUrl(url) for url in dataset_config["applicable_legislation"]
    ]

    # Publisher identifiers
    publisher_identifiers = [
        LiteralField(value=identifier) for identifier in publisher_config["identifier"]
    ]

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