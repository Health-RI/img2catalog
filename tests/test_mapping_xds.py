import pytest
from sempyro.time import PeriodOfTime

from img2catalog.mappings.xds import format_temporal_coverage


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
    assert result.start_date == "01-01-2026"
    assert result.end_date == "31-12-2026"

def test_format_title_returns_formatted_string():
    return

def test_format_title_raises_error_on_missing_field():
    return

def test_map_xds_to_healthri_dcat_dataset_returns_model():
    return

def test_map_xds_to_healthri_dcat_dataset_raises_on_missing_field ():
    return
