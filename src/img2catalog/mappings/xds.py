import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from pandas import Series
from pydantic import AnyHttpUrl
from rdflib import URIRef
from sempyro import LiteralField
from sempyro.dcat import AccessRights
from sempyro.hri_dcat import DatasetTheme, HRIAgent, HRIDataset, HRIVCard
from sempyro.time import PeriodOfTime


def format_temporal_coverage(temporal_coverage: str) -> PeriodOfTime:
    """Format 'DD-MM-YYYY to DD-MM-YYYY' into a PeriodOfTime object."""
    start_str, end_str = temporal_coverage.split("to")

    date_fmt = "%d-%m-%Y"
    start_date = datetime.strptime(start_str.strip(), date_fmt)
    end_date = datetime.strptime(end_str.strip(), date_fmt)

    return PeriodOfTime(
        start_date=LiteralField(value=start_date.strftime(date_fmt)),
        end_date=LiteralField(value=end_date.strftime(date_fmt)),
    )


def format_temporal_coverage_iso(temporal_coverage: str) -> PeriodOfTime:
    """Format 'DD-MM-YYYY to DD-MM-YYYY' into a PeriodOfTime with ISO 8601 (xsd:date) dates.

    This is the value that is set on the dataset, as opposed to :func:`format_temporal_coverage`
    which keeps the day-first notation that is used in the dataset title.
    """
    period = format_temporal_coverage(temporal_coverage)
    date_fmt = "%d-%m-%Y"

    def to_iso(literal: LiteralField) -> LiteralField:
        iso_date = datetime.strptime(literal.value, date_fmt).date().isoformat()
        return LiteralField(value=iso_date, datatype="xsd:date")

    return PeriodOfTime(start_date=to_iso(period.start_date), end_date=to_iso(period.end_date))


def _optional_text(row: Series, column: str) -> Optional[str]:
    """Return the stripped text in an optional column, or None if the column is absent or empty."""
    if column not in row.index:
        return None
    value = row[column]
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _split_keywords(text: str) -> List[str]:
    """Split a keyword cell on semicolons or commas, dropping empty items."""
    return [keyword.strip() for keyword in re.split(r"[;,]", text) if keyword.strip()]


def format_date(start_date: str, end_date: str):
    # Get year from full start and end date
    year_start = start_date.rsplit("-", maxsplit=1)[-1]
    year_end = end_date.rsplit("-", maxsplit=1)[-1]

    # Date formatting logic
    if year_start == year_end:  # e.g: 01-01-2025 == 31-12-2025 -> return 2025
        return year_start
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
        raise KeyError(f"Missing required field in data: {e}") from e

    return f"{institute} - {modality} - {formatted_date_range}"


def format_identifier(prefix: Optional[str] = None) -> str:
    """Build a dataset identifier from a prefix and a UUID.

    The result is `<prefix>/<uuid>`, so that every dataset has an identifier of its own. Without a prefix, the UUID
    is used as is. The UUID is new on every call: the same row gets another identifier when processed again.
    """
    suffix = str(uuid.uuid4())
    if not prefix:
        return suffix
    return f"{prefix.rstrip('/')}/{suffix}"


def map_xds_to_healthri_dcat_dataset(row: Series, config: Dict) -> HRIDataset:
    dataset_config = config.get("dataset")
    publisher_config = dataset_config["publisher"]
    contact_point_config = dataset_config["contact_point"]
    dataset_formatted_title = format_title(row)

    dataset_themes = [DatasetTheme(URIRef(theme)) for theme in dataset_config["theme"]]

    # Optional CSV columns take precedence over the configuration
    keywords_cell = _optional_text(row, "keywords")
    keyword_values = _split_keywords(keywords_cell) if keywords_cell else dataset_config.get("keyword", [])
    dataset_keywords = [LiteralField(value=keyword) for keyword in keyword_values]

    description = _optional_text(row, "description") or dataset_config.get("description")
    dataset_identifier = format_identifier(dataset_config.get("identifier"))
    temporal_coverage = format_temporal_coverage_iso(row["temporalCoverage"])

    dataset_applicable_legislation = [AnyHttpUrl(url) for url in dataset_config["applicable_legislation"]]

    publisher_identifiers = [LiteralField(value=value) for value in publisher_config["identifier"]]

    # Initialize Health-RI Models
    publisher = HRIAgent(
        name=[LiteralField(value=row["instituteName"])],
        identifier=publisher_identifiers,
        mbox=publisher_config["mbox"],
        homepage=publisher_config["homepage"],
    )

    contact_point = HRIVCard(
        hasEmail=contact_point_config["email"],
        formatted_name=contact_point_config["formatted_name"],
    )

    return HRIDataset(
        # MANDATORY DCAT FIELDS
        identifier=LiteralField(value=dataset_identifier),
        title=[LiteralField(value=dataset_formatted_title)],
        description=[LiteralField(value=description)],
        publisher=publisher,
        contact_point=contact_point,
        theme=dataset_themes,
        keyword=dataset_keywords,
        access_rights=AccessRights(URIRef(dataset_config["access_rights"])),
        creator=[publisher],
        applicable_legislation=dataset_applicable_legislation,
        temporal_coverage=[temporal_coverage],
        # CSV FIELDS
        number_of_unique_individuals=int(row["numberOfUniqueIndividuals"]),
        number_of_records=int(row["numberOfRecords"]),
        minimum_typical_age=int(row["minTypicalAge"]),
        maximum_typical_age=int(row["maxTypicalAge"]),
    )
