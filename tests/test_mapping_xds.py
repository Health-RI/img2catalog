import pytest
from sempyro.time import PeriodOfTime

from img2catalog.mappings.xds import format_temporal_coverage, format_title

def get_default_csv_data():
    return {
        "modality": "CT",
        "instituteName": "Amsterdam Hospital",
        "temporalCoverage": "01-01-2026 to 31-12-2026",
        "numberOfUniqueIndividuals": "200",
        "numberOfRecords": "100",
        "minTypicalAge": "18",
        "maxTypicalAge": "60",
    }

def get_missing_csv_data():
    return {
        "instituteName": "Amsterdam Hospital",
    }

def get_default_config():
    return {
        "agent": {
            "identifier": "agent-001",
            "mbox": "mailto:info@amsterdamhospital.nl",
            "homepage": "https://amsterdamhospital.nl",
        },
        "v_card": {
            "has_email": "mailto:info@amsterdamhospital.nl",
            "formatted_name": "Amsterdam Hospital",
        },
        "dataset": {
            "identifier": "dataset-001",
            "description": "A test dataset",
            "theme": ["https://example.com/theme/radiology"],
            "keyword": ["CT", "imaging"],
            "access_rights": "https://example.com/access/restricted",
            "applicable_legislation": ["https://example.com/legislation/gdpr"],
        },
    }

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

def test_format_title_returns_formatted_string():
    # Arrange
    data = get_default_csv_data()
    expected_result = "Amsterdam Hospital_CT_01-01-2026_31-12-2026"

    # Act
    result = format_title(data)

    # Assert
    assert result == expected_result

def test_format_title_raises_error_on_missing_field():
    # Arrange
    data = get_missing_csv_data()

    # Act & Assert
    with pytest.raises(KeyError):
        format_title(data)

def test_map_xds_to_healthri_dcat_dataset_returns_model():
    data = {

    }
    return

def test_map_xds_to_healthri_dcat_dataset_raises_on_missing_field ():
    return
