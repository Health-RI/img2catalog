from datetime import datetime

import pytest
from pydantic import AnyHttpUrl, ValidationError
from rdflib import URIRef
from sempyro.dcat import AccessRights
from sempyro.hri_dcat import DatasetStatus, HRIDataset

from img2catalog.mappings.ega import (
    get_contact_page,
    get_description,
    get_identifier,
    get_keyword,
    get_number_of_records,
    get_release_date,
    get_title,
    map_ega_to_healthri_dcat_dataset,
)


def test_get_identifier_builds_ega_archive_url(default_ega_dataset):
    result = get_identifier(default_ega_dataset)

    assert result == "https://ega-archive.org/datasets/EGAD00001005083"


def test_get_title_returns_title(default_ega_dataset):
    result = get_title(default_ega_dataset)

    assert result == "300-Obese cohort gut microbiome data"


def test_get_title_raises_on_missing_field(missing_ega_dataset):
    with pytest.raises(KeyError):
        get_title(missing_ega_dataset)


def test_get_description_returns_description(default_ega_dataset):
    result = get_description(default_ega_dataset)

    assert result == default_ega_dataset["description"]


def test_get_description_raises_on_missing_field(missing_ega_dataset):
    with pytest.raises(KeyError):
        get_description(missing_ega_dataset)


def test_get_number_of_records_returns_num_samples(default_ega_dataset):
    result = get_number_of_records(default_ega_dataset)

    assert result == 297


def test_get_number_of_records_returns_none_when_missing(missing_ega_dataset):
    result = get_number_of_records(missing_ega_dataset)

    assert result is None


def test_get_release_date_parses_iso_string(default_ega_dataset):
    result = get_release_date(default_ega_dataset)

    assert result == datetime.fromisoformat(default_ega_dataset["released_date"])
    assert isinstance(result, datetime)


def test_get_release_date_returns_none_when_missing(missing_ega_dataset):
    result = get_release_date(missing_ega_dataset)

    assert result is None


def test_get_release_date_passes_through_unparseable_value(default_ega_dataset, caplog):
    default_ega_dataset["released_date"] = "not-a-date"

    result = get_release_date(default_ega_dataset)

    assert result == "not-a-date"
    assert "Could not parse EGA release date" in caplog.text


def test_get_keyword_maps_technologies(default_ega_dataset):
    result = get_keyword(default_ega_dataset)

    assert [keyword.value for keyword in result] == ["Illumina HiSeq 2000"]


def test_get_contact_page_builds_dac_urls(default_ega_dataset):
    result = get_contact_page(default_ega_dataset)

    assert result == ["https://ega-archive.org/dacs/EGAC00001001143"]


def test_get_contact_page_returns_empty_without_dacs(missing_ega_dataset):
    result = get_contact_page(missing_ega_dataset)

    assert result == []


def test_map_ega_to_healthri_dcat_dataset_returns_model(default_ega_dataset, default_config):
    # Act
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, default_config)

    # Assert
    assert isinstance(result, HRIDataset)
    assert result.identifier.value == "https://ega-archive.org/datasets/EGAD00001005083"
    assert result.title[0].value == "300-Obese cohort gut microbiome data"
    assert result.description[0].value == default_ega_dataset["description"]
    assert result.release_date == datetime.fromisoformat(default_ega_dataset["released_date"])
    # HRIDataset uses `use_enum_values=True`, so enum fields are stored as their raw URIRef value.
    assert result.access_rights == AccessRights.public.value
    assert result.number_of_records == 297
    keyword_values = {keyword.value for keyword in result.keyword}
    assert "Illumina HiSeq 2000" in keyword_values
    assert result.theme == [URIRef(theme) for theme in default_config["dataset"]["theme"]]
    assert result.applicable_legislation == [
        AnyHttpUrl(url) for url in default_config["dataset"]["applicable_legislation"]
    ]


def test_map_ega_to_healthri_dcat_dataset_maps_publisher_and_contact_point(default_ega_dataset, default_config):
    # Act
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, default_config)

    # Assert
    publisher_config = default_config["dataset"]["publisher"]
    assert [name.value for name in result.publisher.name] == publisher_config["name"]
    assert [identifier.value for identifier in result.publisher.identifier] == publisher_config["identifier"]
    assert str(result.publisher.mbox) == publisher_config["mbox"]
    assert str(result.publisher.homepage) == publisher_config["homepage"] + "/"

    contact_point_config = default_config["dataset"]["contact_point"]
    assert str(result.contact_point.hasEmail) == contact_point_config["email"]
    assert result.contact_point.formatted_name == contact_point_config["formatted_name"]
    assert result.contact_point.contact_page == [AnyHttpUrl("https://ega-archive.org/dacs/EGAC00001001143")]

    # EGA metadata does not distinguish creator from publisher, so the same agent is used for both.
    assert result.creator == [result.publisher]


def test_map_ega_to_healthri_dcat_dataset_without_dacs_has_no_contact_page(default_ega_dataset, default_config):
    del default_ega_dataset["dacs"]

    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, default_config)

    assert result.contact_point.contact_page is None


def test_map_ega_to_healthri_dcat_dataset_leaves_optional_fields_empty(default_ega_dataset, default_config):
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, default_config)

    assert result.type is None
    assert result.personal_data is None
    assert result.language is None
    assert result.geographical_coverage is None
    assert result.status is None
    assert result.minimum_typical_age is None
    assert result.population_coverage is None
    assert result.publisher.publisher_type is None


def test_map_ega_to_healthri_dcat_dataset_maps_optional_config_fields(default_ega_dataset, default_config):
    # Arrange
    default_config["dataset"].update(
        {
            "type": ["http://publications.europa.eu/resource/authority/dataset-type/STATISTICAL"],
            "personal_data": ["https://w3id.org/dpv/pd#DNACode"],
            "language": ["http://publications.europa.eu/resource/authority/language/ENG"],
            "spatial": ["http://publications.europa.eu/resource/authority/country/NLD"],
            "health_theme": ["https://www.wikidata.org/wiki/Q12174"],
            "legal_basis": ["https://w3id.org/dpv#Consent"],
            "purpose": ["https://w3id.org/dpv#NonCommercialResearch"],
            "code_values": ["https://icd.who.int/browse10/2019/en#/E65-E68"],
            "is_referenced_by": ["https://doi.org/10.1016/j.chom.2020.05.013"],
            "status": "http://publications.europa.eu/resource/authority/dataset-status/COMPLETED",
            "minimum_typical_age": 55,
            "number_of_unique_individuals": 377,
            "population_coverage": "adults aged >55 years and BMI>27 kg/m2",
        }
    )
    default_config["dataset"]["publisher"]["publisher_type"] = (
        "http://purl.org/adms/publishertype/Academia-ScientificOrganisation"
    )

    # Act
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, default_config)

    # Assert
    dataset_config = default_config["dataset"]
    assert result.type == [AnyHttpUrl(url) for url in dataset_config["type"]]
    assert result.personal_data == [AnyHttpUrl(url) for url in dataset_config["personal_data"]]
    assert result.language == [AnyHttpUrl(url) for url in dataset_config["language"]]
    assert result.geographical_coverage == [AnyHttpUrl(url) for url in dataset_config["spatial"]]
    assert result.health_theme == [AnyHttpUrl(url) for url in dataset_config["health_theme"]]
    assert result.legal_basis == [AnyHttpUrl(url) for url in dataset_config["legal_basis"]]
    assert result.purpose == [AnyHttpUrl(url) for url in dataset_config["purpose"]]
    assert result.code_values == [AnyHttpUrl(url) for url in dataset_config["code_values"]]
    assert result.is_referenced_by == [AnyHttpUrl(url) for url in dataset_config["is_referenced_by"]]
    assert result.status == DatasetStatus.completed.value
    assert result.minimum_typical_age == 55
    assert result.number_of_unique_individuals == 377
    assert result.population_coverage.value == dataset_config["population_coverage"]
    assert str(result.publisher.publisher_type) == dataset_config["publisher"]["publisher_type"]


def test_map_ega_to_healthri_dcat_dataset_raises_on_missing_field(missing_ega_dataset, default_config):
    # Act & Assert
    with pytest.raises(KeyError):
        map_ega_to_healthri_dcat_dataset(missing_ega_dataset, default_config)


def test_map_ega_to_healthri_dcat_dataset_raises_without_dataset_config(default_ega_dataset):
    # Act & Assert
    with pytest.raises((KeyError, ValidationError)):
        map_ega_to_healthri_dcat_dataset(default_ega_dataset, {})
