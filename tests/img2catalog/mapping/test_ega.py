import pytest
from pydantic import ValidationError
from rdflib import URIRef
from sempyro.dcat import AccessRights
from sempyro.hri_dcat import DatasetStatus, HRIDataset

from img2catalog.mappings.ega import get_keyword, map_ega_to_healthri_dcat_dataset


def test_map_status_deprecated_takes_priority():
    assert map_status(is_released=True, is_deprecated=True) == DatasetStatus.deprecated


def test_map_status_released_and_not_deprecated():
    assert map_status(is_released=True, is_deprecated=False) == DatasetStatus.completed


def test_map_status_not_released_and_not_deprecated():
    assert map_status(is_released=False, is_deprecated=False) == DatasetStatus.develop


def test_map_access_type_public(default_config):
    assert map_access_type("public", default_config) == AccessRights.public


def test_map_access_type_controlled(default_config):
    assert map_access_type("controlled", default_config) == AccessRights.restricted


def test_map_access_type_unrecognised_falls_back_to_configured_default(default_config):
    result = map_access_type("unknown", default_config)

    assert result == AccessRights(URIRef(default_config["dataset"]["access_rights"]))


def test_get_keyword_maps_technologies(default_ega_dataset):
    result = get_keyword(default_ega_dataset)

    assert [keyword.value for keyword in result] == ["Illumina HiSeq 2000"]


def test_map_ega_to_healthri_dcat_dataset_returns_model(default_ega_dataset, default_config):
    # Act
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, default_config)

    # Assert
    assert isinstance(result, HRIDataset)
    assert result.identifier.value == "http://identifiers.org/ega.dataset:EGAD00001005083"
    assert result.title[0].value == "300-Obese cohort gut microbiome data"
    # HRIDataset uses `use_enum_values=True`, so enum fields are stored as their raw URIRef value.
    assert result.status == DatasetStatus.completed.value
    assert result.access_rights == AccessRights.restricted.value
    assert result.number_of_records == 297
    keyword_values = {keyword.value for keyword in result.keyword}
    assert "Illumina HiSeq 2000" in keyword_values


def test_map_ega_to_healthri_dcat_dataset_raises_on_missing_field(missing_ega_dataset, default_config):
    # Act & Assert
    with pytest.raises(KeyError):
        map_ega_to_healthri_dcat_dataset(missing_ega_dataset, default_config)


def test_map_ega_to_healthri_dcat_dataset_raises_without_dataset_config(default_ega_dataset):
    # Act & Assert
    with pytest.raises((KeyError, ValidationError)):
        map_ega_to_healthri_dcat_dataset(default_ega_dataset, {})
