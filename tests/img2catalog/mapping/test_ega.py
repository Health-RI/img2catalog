from datetime import datetime

import pytest
from pydantic import AnyHttpUrl, ValidationError
from rdflib import URIRef
from sempyro.dcat import AccessRights
from sempyro.hri_dcat import DatasetStatus, HRICatalog, HRIDataset

from img2catalog.mappings.ega import (
    get_contact_page,
    get_description,
    get_file_type,
    get_identifier,
    get_keyword,
    get_number_of_records,
    get_qualified_attribution,
    get_release_date,
    get_title,
    map_ega_to_healthri_dcat_catalog,
    map_ega_to_healthri_dcat_dataset,
    map_ega_to_healthri_dcat_distributions,
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


def test_get_qualified_attribution_maps_main_dac_contact(default_ega_dataset):
    result = get_qualified_attribution(default_ega_dataset, {})

    assert len(result) == 1
    agent = result[0].agent
    assert [name.value for name in agent.name] == ["John Doe"]
    assert agent.identifier.value == "https://ega-archive.org/dacs/EGAC00001001143"
    assert [str(mbox) for mbox in agent.mbox] == ["mailto:dac@example.com"]
    assert result[0].role is None


def test_get_qualified_attribution_uses_configured_role(default_ega_dataset):
    role = "https://standards.iso.org/iso/19115/resources/Codelists/gml/CI_RoleCode.xml#principalInvestigator"

    result = get_qualified_attribution(default_ega_dataset, {"qualified_attribution": {"role": role}})

    assert str(result[0].role) == role


def test_get_qualified_attribution_skips_non_main_contacts(default_ega_dataset):
    default_ega_dataset["dacs"][0]["contacts"][0]["is_main"] = False

    result = get_qualified_attribution(default_ega_dataset, {})

    assert result == []


def test_get_qualified_attribution_returns_empty_without_dacs(missing_ega_dataset):
    result = get_qualified_attribution(missing_ega_dataset, {})

    assert result == []


@pytest.mark.parametrize(
    ("extension", "expected"),
    [
        ("bam", "http://publications.europa.eu/resource/authority/file-type/BIN"),
        ("cram", "http://publications.europa.eu/resource/authority/file-type/BIN"),
        ("vcf", "http://publications.europa.eu/resource/authority/file-type/TXT"),
        ("SAM", "http://publications.europa.eu/resource/authority/file-type/TXT"),
        (None, "http://publications.europa.eu/resource/authority/file-type/BIN"),
    ],
)
def test_get_file_type_maps_extension(extension, expected):
    assert get_file_type({"extension": extension}) == expected


def test_map_ega_to_healthri_dcat_distributions_combines_files(default_ega_dataset, ega_config):
    # Act
    result = map_ega_to_healthri_dcat_distributions(default_ega_dataset, ega_config)

    # Assert
    distribution_config = ega_config["distribution"]
    assert len(result) == 1
    distribution = result[0]
    assert str(distribution.access_url) == "https://ega-archive.org/datasets/EGAD00001005083"
    assert distribution.byte_size == 3000
    assert distribution.description[0].value == default_ega_dataset["description"]
    assert str(distribution.format) == "http://publications.europa.eu/resource/authority/file-type/BIN"
    assert distribution.language == [AnyHttpUrl(url) for url in distribution_config["language"]]
    assert str(distribution.license) == distribution_config["license"]
    assert distribution.release_date == datetime.fromisoformat(default_ega_dataset["released_date"])
    assert str(distribution.rights) == "https://ega-archive.org/datasets/EGAD00001005083"
    assert distribution.title[0].value == default_ega_dataset["title"]


def test_map_ega_to_healthri_dcat_distributions_splits_per_format(default_ega_dataset, ega_config):
    # Arrange
    default_ega_dataset["files"].append({"accession_id": "EGAF00000000003", "filesize": 500, "extension": "vcf"})

    # Act
    result = map_ega_to_healthri_dcat_distributions(default_ega_dataset, ega_config)

    # Assert
    sizes_per_format = {str(distribution.format): distribution.byte_size for distribution in result}
    assert sizes_per_format == {
        "http://publications.europa.eu/resource/authority/file-type/BIN": 3000,
        "http://publications.europa.eu/resource/authority/file-type/TXT": 500,
    }


def test_map_ega_to_healthri_dcat_distributions_returns_empty_without_files(missing_ega_dataset):
    result = map_ega_to_healthri_dcat_distributions(missing_ega_dataset, {})

    assert result == []


def test_map_ega_to_healthri_dcat_distributions_raises_without_license(default_ega_dataset):
    with pytest.raises(KeyError):
        map_ega_to_healthri_dcat_distributions(default_ega_dataset, {"distribution": {}})


def test_map_ega_to_healthri_dcat_dataset_returns_model(default_ega_dataset, ega_config):
    # Act
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

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
    assert result.theme == [URIRef(theme) for theme in ega_config["dataset"]["theme"]]
    assert result.applicable_legislation == [AnyHttpUrl(url) for url in ega_config["dataset"]["applicable_legislation"]]


def test_map_ega_to_healthri_dcat_dataset_maps_publisher_and_contact_point(default_ega_dataset, ega_config):
    # Act
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    # Assert
    publisher_config = ega_config["dataset"]["publisher"]
    assert [name.value for name in result.publisher.name] == publisher_config["name"]
    assert [identifier.value for identifier in result.publisher.identifier] == publisher_config["identifier"]
    assert str(result.publisher.mbox) == publisher_config["mbox"]
    assert str(result.publisher.homepage) == publisher_config["homepage"] + "/"

    contact_point_config = ega_config["dataset"]["contact_point"]
    assert str(result.contact_point.hasEmail) == contact_point_config["email"]
    assert result.contact_point.formatted_name == contact_point_config["formatted_name"]
    assert result.contact_point.contact_page == [AnyHttpUrl("https://ega-archive.org/dacs/EGAC00001001143")]

    # EGA metadata does not distinguish creator from publisher, so the same agent is used for both.
    assert result.creator == [result.publisher]


def test_map_ega_to_healthri_dcat_dataset_without_dacs_has_no_contact_page(default_ega_dataset, ega_config):
    del default_ega_dataset["dacs"]

    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    assert result.contact_point.contact_page is None
    assert result.qualified_attribution is None


def test_map_ega_to_healthri_dcat_dataset_maps_distribution(default_ega_dataset, ega_config):
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    assert len(result.distribution) == 1
    assert result.distribution[0].byte_size == 3000


def test_map_ega_to_healthri_dcat_dataset_without_files_has_no_distribution(default_ega_dataset, ega_config):
    default_ega_dataset["files"] = []

    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    assert result.distribution is None


def test_map_ega_to_healthri_dcat_dataset_maps_qualified_attribution(default_ega_dataset, ega_config):
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    assert len(result.qualified_attribution) == 1
    assert result.qualified_attribution[0].agent.identifier.value == "https://ega-archive.org/dacs/EGAC00001001143"


def test_map_ega_to_healthri_dcat_dataset_leaves_optional_fields_empty(default_ega_dataset, ega_config):
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    assert result.type is None
    assert result.personal_data is None
    assert result.language is None
    assert result.geographical_coverage is None
    assert result.status is None
    assert result.minimum_typical_age is None
    assert result.population_coverage is None
    assert result.publisher.publisher_type is None


def test_map_ega_to_healthri_dcat_dataset_maps_optional_config_fields(default_ega_dataset, ega_config):
    # Arrange
    ega_config["dataset"].update(
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
    ega_config["dataset"]["publisher"]["publisher_type"] = (
        "http://purl.org/adms/publishertype/Academia-ScientificOrganisation"
    )

    # Act
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    # Assert
    dataset_config = ega_config["dataset"]
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


def test_map_ega_to_healthri_dcat_dataset_raises_on_missing_field(missing_ega_dataset, ega_config):
    # Act & Assert
    with pytest.raises(KeyError):
        map_ega_to_healthri_dcat_dataset(missing_ega_dataset, ega_config)


def test_map_ega_to_healthri_dcat_dataset_raises_without_dataset_config(default_ega_dataset):
    # Act & Assert
    with pytest.raises((KeyError, ValidationError)):
        map_ega_to_healthri_dcat_dataset(default_ega_dataset, {})


@pytest.fixture
def ega_catalog_config(ega_config):
    ega_config["catalog"] = {
        "title": "Example EGA catalog",
        "description": "This is an example EGA catalog description",
        "contact_point": {
            "formatted_name": "Example Data Management office",
            "email": "mailto:datamanager@example.com",
        },
    }
    return ega_config


def test_map_ega_to_healthri_dcat_catalog_returns_model(ega_catalog_config):
    # Arrange
    dataset_uris = [URIRef("http://img2catalog.internal/dataset/EGAD00001005083")]

    # Act
    result = map_ega_to_healthri_dcat_catalog(ega_catalog_config, dataset_uris)

    # Assert
    catalog_config = ega_catalog_config["catalog"]
    assert isinstance(result, HRICatalog)
    assert result.title[0].value == catalog_config["title"]
    assert result.description[0].value == catalog_config["description"]
    assert [str(dataset) for dataset in result.dataset] == [str(uri) for uri in dataset_uris]
    assert str(result.contact_point.hasEmail) == catalog_config["contact_point"]["email"]
    assert result.contact_point.formatted_name == catalog_config["contact_point"]["formatted_name"]
    # The institute publishing the datasets is also the creator and publisher of the catalog
    publisher_config = ega_catalog_config["dataset"]["publisher"]
    assert [name.value for name in result.publisher.name] == publisher_config["name"]
    assert result.creator == [result.publisher]
    assert result.geographical_coverage is None
    assert result.language is None
    assert result.release_date is None


def test_map_ega_to_healthri_dcat_catalog_maps_optional_config_fields(ega_catalog_config):
    # Arrange
    ega_catalog_config["catalog"].update(
        {
            "spatial": ["http://publications.europa.eu/resource/authority/country/NLD"],
            "language": ["http://publications.europa.eu/resource/authority/language/ENG"],
            "release_date": "2019-06-10T00:00:00Z",
        }
    )

    # Act
    result = map_ega_to_healthri_dcat_catalog(ega_catalog_config, [])

    # Assert
    catalog_config = ega_catalog_config["catalog"]
    assert result.geographical_coverage == [AnyHttpUrl(url) for url in catalog_config["spatial"]]
    assert result.language == [AnyHttpUrl(url) for url in catalog_config["language"]]
    assert result.release_date == datetime.fromisoformat("2019-06-10T00:00:00+00:00")


def test_map_ega_to_healthri_dcat_catalog_accepts_toml_datetime(ega_catalog_config):
    release_date = datetime.fromisoformat("2019-06-10T00:00:00+00:00")
    ega_catalog_config["catalog"]["release_date"] = release_date

    result = map_ega_to_healthri_dcat_catalog(ega_catalog_config, [])

    assert result.release_date == release_date


def test_map_ega_to_healthri_dcat_catalog_raises_without_catalog_config(ega_config):
    with pytest.raises(KeyError):
        map_ega_to_healthri_dcat_catalog(ega_config, [])
