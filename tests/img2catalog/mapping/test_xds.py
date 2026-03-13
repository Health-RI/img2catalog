import pytest
from pandas import Series
from sempyro.hri_dcat import HRIDataset
from sempyro.time import PeriodOfTime

from img2catalog.mappings.xds import format_temporal_coverage, format_title, map_xds_to_healthri_dcat_dataset

def test_format_temporal_coverage_raises_value_error():
    # Arrange
    invalid_temporal_coverage = "01-01-2026_31-12-2026"

    # Act & Assert
    with pytest.raises(ValueError):
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

def test_format_title_returns_formatted_string(default_csv_data):
    # Arrange
    expected_result = "Amsterdam Hospital - CT - 01-01-2026/31-12-2026"

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
