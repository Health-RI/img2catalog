import uuid

import pytest
from rdflib import XSD
from sempyro.hri_dcat import HRIDataset
from sempyro.time import PeriodOfTime

from img2catalog.mappings.xds import (
    format_date,
    format_identifier,
    format_temporal_coverage,
    format_temporal_coverage_iso,
    format_title,
    map_xds_to_healthri_dcat_dataset,
)


def test_format_temporal_coverage_raises_value_error():
    # Arrange
    invalid_temporal_coverage = "01-01-2026_31-12-2026"

    # Act & Assert
    with pytest.raises(ValueError, match="not enough values to unpack"):
        format_temporal_coverage(invalid_temporal_coverage)


def test_format_temporal_coverage_returns_valid_periodoftime():
    # Arrange
    temporal_coverage = "01-01-2026 to 31-12-2026"

    # Act
    result = format_temporal_coverage(temporal_coverage)

    # Assert
    assert isinstance(result, PeriodOfTime)
    assert result.start_date.value == "01-01-2026"
    assert result.end_date.value == "31-12-2026"


def test_same_year_returns_single_year():
    # Arrange
    start = "01-01-2026"
    end = "31-12-2026"

    # Act
    result = format_date(start, end)

    # Assert
    assert result == "2026"


def test_different_years_returns_range():
    # Arrange
    start = "01-01-2024"
    end = "31-12-2026"

    # Act
    result = format_date(start, end)

    # Assert
    assert result == "01-01-2024/31-12-2026"


def test_format_title_returns_formatted_string(default_csv_data):
    # Arrange
    expected_result = "Amsterdam Hospital - CT - 2026"

    # Act
    result = format_title(default_csv_data)

    # Assert
    assert result == expected_result


def test_format_title_raises_error_on_missing_field(missing_csv_data):
    # Act & Assert
    with pytest.raises(KeyError):
        format_title(missing_csv_data)


def test_map_xds_to_healthri_dcat_dataset_returns_model(default_csv_data, default_config):
    # Act
    result = map_xds_to_healthri_dcat_dataset(default_csv_data, default_config)

    # Assert
    assert isinstance(result, HRIDataset)
    assert result.number_of_unique_individuals == 200
    assert result.number_of_records == 100
    assert result.minimum_typical_age == 18
    assert result.maximum_typical_age == 65


def test_map_xds_to_healthri_dcat_dataset_raises_on_missing_field(missing_csv_data, default_config):
    # Act & Assert
    with pytest.raises(KeyError):
        map_xds_to_healthri_dcat_dataset(missing_csv_data, default_config)


@pytest.mark.parametrize("prefix", ["https://www.example.com/img-123", "https://www.example.com/img-123/"])
def test_format_identifier_is_prefix_followed_by_uuid(prefix):
    result = format_identifier(prefix)

    base, _, suffix = result.rpartition("/")
    assert base == "https://www.example.com/img-123"
    assert str(uuid.UUID(suffix)) == suffix


@pytest.mark.parametrize("prefix", [None, ""])
def test_format_identifier_without_prefix_is_a_uuid(prefix):
    result = format_identifier(prefix)

    assert str(uuid.UUID(result)) == result


def test_format_identifier_generates_a_new_uuid_each_time():
    assert format_identifier("https://www.example.com/img-123") != format_identifier("https://www.example.com/img-123")


def test_map_xds_gives_each_row_its_own_generated_identifier(default_csv_data, default_config):
    """Every dataset gets an identifier of its own: the configured prefix followed by a UUID."""
    datasets = [map_xds_to_healthri_dcat_dataset(default_csv_data, default_config) for _ in range(2)]
    identifiers = [dataset.identifier.value for dataset in datasets]

    assert len(set(identifiers)) == 2
    for identifier in identifiers:
        prefix, _, suffix = identifier.rpartition("/")
        assert prefix == "https://www.example.com/img-123"
        assert str(uuid.UUID(suffix)) == suffix


def test_map_xds_without_configured_prefix_uses_a_uuid(default_csv_data, default_config):
    del default_config["dataset"]["identifier"]

    result = map_xds_to_healthri_dcat_dataset(default_csv_data, default_config)

    assert str(uuid.UUID(result.identifier.value)) == result.identifier.value


def test_format_temporal_coverage_iso_returns_xsd_dates():
    # Act
    result = format_temporal_coverage_iso("01-01-2022 to 31-12-2023")

    # Assert
    assert result.start_date.value == "2022-01-01"
    assert result.end_date.value == "2023-12-31"
    assert str(result.start_date.datatype) == str(XSD.date)
    assert str(result.end_date.datatype) == str(XSD.date)


def test_format_temporal_coverage_iso_raises_on_malformed_value():
    with pytest.raises(ValueError, match="not enough values to unpack"):
        format_temporal_coverage_iso("2022 until 2023")


def test_format_temporal_coverage_iso_raises_when_end_is_before_start():
    with pytest.raises(ValueError, match="before its start date"):
        format_temporal_coverage_iso("31-12-2024 to 01-01-2024")


def test_format_temporal_coverage_iso_accepts_a_single_day():
    result = format_temporal_coverage_iso("01-01-2024 to 01-01-2024")

    assert result.start_date.value == result.end_date.value == "2024-01-01"


def test_map_raises_on_reversed_temporal_coverage(default_csv_data, default_config):
    row = default_csv_data.copy()
    row["temporalCoverage"] = "31-12-2026 to 01-01-2026"

    with pytest.raises(ValueError, match="before its start date"):
        map_xds_to_healthri_dcat_dataset(row, default_config)


def test_map_sets_temporal_coverage(default_csv_data, default_config):
    # Act
    result = map_xds_to_healthri_dcat_dataset(default_csv_data, default_config)

    # Assert
    assert len(result.temporal_coverage) == 1
    assert result.temporal_coverage[0].start_date.value == "2026-01-01"
    assert result.temporal_coverage[0].end_date.value == "2026-12-31"
