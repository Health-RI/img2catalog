import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import click
from pandas import DataFrame, Series
from pydantic import AnyHttpUrl
from rdflib import URIRef
from sempyro import LiteralField
from sempyro.dcat import AccessRights
from sempyro.hri_dcat import DatasetTheme, HRIAgent, HRIDataset, HRIVCard
from sempyro.time import PeriodOfTime

from img2catalog.mappings.column_mapping import (
    DEFAULT_LIST_SEPARATOR,
    ColumnMappingError,
    map_columns_to_properties,
    validate_column_mapping,
)

logger = logging.getLogger(__name__)

# Properties that are filled from a column of the CSV file, if the user has not mapped a column to them
CSV_NUMBER_COLUMNS = {
    "number_of_unique_individuals": "numberOfUniqueIndividuals",
    "number_of_records": "numberOfRecords",
    "minimum_typical_age": "minTypicalAge",
    "maximum_typical_age": "maxTypicalAge",
}


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
    start_date = datetime.strptime(period.start_date.value, date_fmt).date()
    end_date = datetime.strptime(period.end_date.value, date_fmt).date()
    if end_date < start_date:
        raise ValueError(f"The end date of temporal coverage '{temporal_coverage}' is before its start date")

    return PeriodOfTime(
        start_date=LiteralField(value=start_date.isoformat(), datatype="xsd:date"),
        end_date=LiteralField(value=end_date.isoformat(), datatype="xsd:date"),
    )


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


def format_identifier(prefix: Optional[str] = None, identifier: Optional[str] = None) -> str:
    """Build a dataset identifier from a prefix and, optionally, a given identifier.

    The result is `<prefix>/<identifier>`. When no identifier is given, a UUID takes its place as a fallback, so that
    every dataset has an identifier of its own. Without a prefix, the identifier (or UUID) is used as is.

    A generated UUID is new on every call: the same row gets another identifier when processed again. To make the FDP
    output find a dataset again, map a column of the CSV file to `identifier` (see `[xds.column_mapping]`).
    """
    suffix = identifier or str(uuid.uuid4())
    if not prefix:
        return suffix
    return f"{prefix.rstrip('/')}/{suffix}"


def _row_label(row: Series) -> str:
    """Name the line in the CSV file of a row, counting the header as line 1, so it can be found in an editor."""
    if isinstance(row.name, int):
        return f"Line {row.name + 2}"
    return "A row" if row.name is None else f"Row {row.name}"


def ensure_unique_identifiers(datasets: List[HRIDataset]) -> None:
    """Refuse datasets that get the same identifier, as the FDP would take them for one dataset.

    Generated identifiers are unique, so this only happens when rows have the same value in the column that is mapped
    to `identifier`.
    """
    titles_per_identifier: Dict[str, str] = {}
    for dataset in datasets:
        identifier, title = dataset.identifier.value, dataset.title[0].value
        if identifier in titles_per_identifier:
            raise ValueError(
                f"The XDS rows '{titles_per_identifier[identifier]}' and '{title}' get the same dataset identifier "
                f"'{identifier}', so one would overwrite the other. Give them different identifiers."
            )
        titles_per_identifier[identifier] = title


def map_xds_to_healthri_dcat_dataset(row: Series, config: Dict) -> HRIDataset:
    """Map a row of the XDS CSV file to a Health-RI dataset.

    Raises
    ------
    ValueError
        If the row gives an invalid dataset, e.g. a value that does not fit the property it is mapped to. The message
        names the line in the CSV file.
    """
    try:
        return _map_row(row, config)
    except ValueError as e:
        raise ValueError(f"{_row_label(row)} of the XDS file: {e}") from e


def _map_row(row: Series, config: Dict) -> HRIDataset:
    dataset_config = config.get("dataset")
    publisher_config = dataset_config["publisher"]
    contact_point_config = dataset_config["contact_point"]
    dataset_formatted_title = format_title(row)

    dataset_themes = [DatasetTheme(URIRef(theme)) for theme in dataset_config["theme"]]

    dataset_keywords = [LiteralField(value=keyword) for keyword in dataset_config["keyword"]]

    xds_config = config.get("xds", {})
    # Columns that the user mapped to properties, e.g. a description or keywords per dataset
    mapped_properties = map_columns_to_properties(
        row,
        xds_config.get("column_mapping", {}),
        HRIDataset,
        xds_config.get("list_separator", DEFAULT_LIST_SEPARATOR),
    )
    identifier = mapped_properties.pop("identifier", None)
    dataset_identifier = format_identifier(dataset_config.get("identifier"), identifier)
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

    properties = {
        # MANDATORY DCAT FIELDS
        "identifier": LiteralField(value=dataset_identifier),
        "title": [LiteralField(value=dataset_formatted_title)],
        "description": [LiteralField(value=dataset_config["description"])],
        "publisher": publisher,
        "contact_point": contact_point,
        "theme": dataset_themes,
        "keyword": dataset_keywords,
        "access_rights": AccessRights(URIRef(dataset_config["access_rights"])),
        "creator": [publisher],
        "applicable_legislation": dataset_applicable_legislation,
        "temporal_coverage": [temporal_coverage],
    }
    # CSV FIELDS: the columns that the user mapped to the same property are not read, they take precedence
    for property_name, column in CSV_NUMBER_COLUMNS.items():
        if property_name not in mapped_properties:
            properties[property_name] = int(row[column])
    # What the user mapped from the CSV file takes precedence over the above, which is the configuration and defaults
    properties.update(mapped_properties)

    return HRIDataset(**properties)


def check_column_mapping(csv_rows: DataFrame, config: Dict) -> None:
    """Check the `[xds]` settings for the column mapping of the configuration before mapping the rows.

    Raises
    ------
    click.ClickException
        If the mapping or the list separator cannot be used. Mapped columns that are not in the CSV file only give a
        warning, as the columns are not mandatory.
    """
    xds_config = config.get("xds", {})
    if not isinstance(xds_config, dict):
        raise click.ClickException("Invalid [xds] in the configuration: it must be a table")
    column_mapping = xds_config.get("column_mapping", {})
    if not isinstance(column_mapping, dict):
        raise click.ClickException(
            'Invalid [xds.column_mapping] in the configuration: it must be a table of "column header" = "property"'
        )
    list_separator = xds_config.get("list_separator", DEFAULT_LIST_SEPARATOR)
    if not isinstance(list_separator, str) or not list_separator:
        raise click.ClickException("Invalid list_separator in [xds] in the configuration: it must be a non-empty text")
    try:
        validate_column_mapping(column_mapping, HRIDataset)
    except ColumnMappingError as e:
        raise click.ClickException(f"Invalid [xds.column_mapping] in the configuration: {e}") from e
    for column in column_mapping:
        if column not in csv_rows.columns:
            logger.warning("Column '%s' of [xds.column_mapping] is not in the XDS file, it is skipped", column)
