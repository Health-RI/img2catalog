import pytest
from pandas import Series
from sempyro.hri_dcat import HRIDataset
from sempyro.time import PeriodOfTime

from img2catalog.mappings.xds import format_temporal_coverage, format_title, map_xds_to_healthri_dcat_dataset

def get_default_csv_data():
    return Series({
        "modality": "CT",
        "instituteName": "Amsterdam Hospital",
        "temporalCoverage": "01-01-2026 to 31-12-2026",
        "numberOfUniqueIndividuals": "200",
        "numberOfRecords": "100",
        "minTypicalAge": "18",
        "maxTypicalAge": "65",
    })

def get_missing_csv_data():
    return Series({
        "instituteName": "Amsterdam Hospital",
    })

def get_default_config():
    return {
        "agent": {
            "identifier": "http://www.example.com/institution#example",
            "mbox": "mailto:publisher@example.com",
            "homepage": "http://www.example.com",
        },
        "v_card": {
            "has_email": "mailto:datamanager@example.com",
            "formatted_name": "Example Data Management office",
        },
        "dataset": {
            "identifier": "591c8e28-a621-4d4c-aadb-2f6671ecbaa2",
            "description": "This is an example XNAT catalog description",
            "theme": ["http://publications.europa.eu/resource/authority/data-theme/HEAL"],
            "keyword": ["dataset", "research"],
            "access_rights": "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC",
            "applicable_legislation": ["http://data.europa.eu/eli/reg/2025/327/oj"],
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
    # Arrange
    data = get_default_csv_data()
    config = get_default_config()

    # Act
    result = map_xds_to_healthri_dcat_dataset(data, config)

    # Assert
    assert isinstance(result, HRIDataset)
    assert result.number_of_unique_individuals == 200
    assert result.number_of_records == 100
    assert result.minimum_typical_age == 18
    assert result.maximum_typical_age == 65

def test_map_xds_to_healthri_dcat_dataset_raises_on_missing_field():
    # Arrange
    data = get_missing_csv_data()
    config = get_default_config()

    # Act & Assert
    with pytest.raises(KeyError):
        map_xds_to_healthri_dcat_dataset(data, config)
