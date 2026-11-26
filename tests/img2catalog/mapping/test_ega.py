import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from pydantic import AnyHttpUrl, ValidationError
from rdflib import DCAT, DCTERMS, URIRef
from sempyro.dcat import AccessRights
from sempyro.hri_dcat import DatasetStatus, HRICatalog, HRIDataset

from img2catalog.mappings.ega import (
    FileFormat,
    get_contact_email,
    get_contact_page,
    get_description,
    get_file_format,
    get_identifier,
    get_is_referenced_by,
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


def test_get_title_falls_back_to_accession_id(missing_ega_dataset):
    """EGA has datasets without a title; the title is mandatory, so the accession ID is used."""
    assert get_title(missing_ega_dataset) == "EGAD00001005083"


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


def test_get_release_date_parses_utc_suffix(default_ega_dataset):
    """A trailing "Z" is not parsed by fromisoformat before Python 3.11, so it has to be handled explicitly."""
    default_ega_dataset["released_date"] = "2019-02-28T12:25:33Z"

    result = get_release_date(default_ega_dataset)

    assert result == datetime(2019, 2, 28, 12, 25, 33, tzinfo=timezone.utc)


def test_get_release_date_leaves_out_unparseable_value(default_ega_dataset, caplog):
    default_ega_dataset["released_date"] = "not-a-date"

    with caplog.at_level(logging.ERROR):
        result = get_release_date(default_ega_dataset)

    assert result is None
    assert "Could not parse EGA release date 'not-a-date', so it is left out" in caplog.text


def test_map_ega_to_healthri_dcat_distributions_leaves_out_unparseable_release_date(default_ega_dataset, ega_config):
    default_ega_dataset["released_date"] = "not-a-date"

    result = map_ega_to_healthri_dcat_distributions(default_ega_dataset, ega_config)

    assert all(distribution.release_date is None for distribution in result)


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
    assert str(agent.homepage) == "https://ega-archive.org/dacs/EGAC00001001143"
    assert [str(mbox) for mbox in agent.mbox] == ["mailto:dac@example.com"]
    assert result[0].role is None


def test_get_qualified_attribution_uses_configured_role(default_ega_dataset):
    role = "https://standards.iso.org/iso/19115/resources/Codelists/gml/CI_RoleCode.xml#principalInvestigator"

    result = get_qualified_attribution(default_ega_dataset, {"qualified_attribution": {"role": role}})

    assert str(result[0].role) == role


def test_get_qualified_attribution_leaves_out_null_names(default_ega_dataset):
    """EGA can return a null first name, which must not end up in the name as the text "None"."""
    default_ega_dataset["dacs"][0]["contacts"][0]["first_name"] = None

    result = get_qualified_attribution(default_ega_dataset, {})

    assert [name.value for name in result[0].agent.name] == ["Doe"]


def test_get_qualified_attribution_skips_non_main_contacts(default_ega_dataset):
    default_ega_dataset["dacs"][0]["contacts"][0]["is_main"] = False

    result = get_qualified_attribution(default_ega_dataset, {})

    assert result == []


def test_get_qualified_attribution_returns_empty_without_dacs(missing_ega_dataset):
    result = get_qualified_attribution(missing_ega_dataset, {})

    assert result == []


def test_get_contact_email_returns_main_dac_contact(default_ega_dataset):
    assert get_contact_email(default_ega_dataset) == "mailto:dac@example.com"


def test_get_contact_email_skips_non_main_contacts(default_ega_dataset):
    default_ega_dataset["dacs"][0]["contacts"][0]["is_main"] = False

    assert get_contact_email(default_ega_dataset) is None


def test_get_contact_email_returns_none_without_dacs(missing_ega_dataset):
    assert get_contact_email(missing_ega_dataset) is None


def test_get_is_referenced_by_builds_pubmed_urls(default_ega_dataset):
    default_ega_dataset["studies"].append({"accession_id": "EGAS2", "pubmed_ids": ["32526207", 37000000]})

    assert get_is_referenced_by(default_ega_dataset) == [
        "https://pubmed.ncbi.nlm.nih.gov/32526207/",
        "https://pubmed.ncbi.nlm.nih.gov/37000000/",
    ]


def test_get_is_referenced_by_handles_studies_without_publications(default_ega_dataset, missing_ega_dataset):
    default_ega_dataset["studies"][0]["pubmed_ids"] = None

    assert get_is_referenced_by(default_ega_dataset) == []
    assert get_is_referenced_by(missing_ega_dataset) == []


BIN = "http://publications.europa.eu/resource/authority/file-type/BIN"
TXT = "http://publications.europa.eu/resource/authority/file-type/TXT"
GZIP = "http://www.iana.org/assignments/media-types/application/gzip"
ZSTD = "http://www.iana.org/assignments/media-types/application/zstd"
EGA_EXAMPLES = Path(__file__).parent.parent / "examples" / "ega"


@pytest.mark.parametrize(
    ("extension", "expected"),
    [
        ("bam", FileFormat(BIN, None, known=True)),
        ("cram", FileFormat(BIN, None, known=True)),
        ("vcf", FileFormat(TXT, None, known=True)),
        ("SAM", FileFormat(TXT, None, known=True)),
        ("fastq", FileFormat(TXT, None, known=True)),
        ("fasta", FileFormat(TXT, None, known=True)),
        ("bed", FileFormat(TXT, None, known=True)),
        ("gff", FileFormat(TXT, None, known=True)),
        # Extensions as EGA gives them for compressed files: the format of the data, compressed
        ("vcf.gz", FileFormat(TXT, GZIP, known=True)),
        ("fastq.gz", FileFormat(TXT, GZIP, known=True)),
        ("CEL.gz", FileFormat(BIN, GZIP, known=True)),
        ("tar.gz", FileFormat(BIN, GZIP, known=True)),
        ("vcf.bgz", FileFormat(TXT, GZIP, known=True)),
        ("tsv.zst", FileFormat(TXT, ZSTD, known=True)),
        (".vcf.gz", FileFormat(TXT, GZIP, known=True)),
        # Compressed, but the format of the data is unknown
        ("gz", FileFormat(BIN, GZIP, known=False)),
        # EGA gives numbers as extension for some files
        ("1664408722194", FileFormat(BIN, None, known=False)),
        (None, FileFormat(BIN, None, known=False)),
        ("", FileFormat(BIN, None, known=False)),
    ],
)
def test_get_file_format_maps_extension(extension, expected):
    assert get_file_format({"extension": extension}) == expected


def test_map_ega_to_healthri_dcat_distributions_maps_real_ega_file_listing(default_ega_dataset, ega_config, caplog):
    """The files of EGAD00001003338 as the EGA metadata API returns them (one file per extension)."""
    # Arrange
    default_ega_dataset["files"] = json.loads((EGA_EXAMPLES / "files_EGAD00001003338.json").read_text())

    # Act
    with caplog.at_level(logging.WARNING):
        result = map_ega_to_healthri_dcat_distributions(default_ega_dataset, ega_config)

    # Assert
    # cram, crai, bam, bai, tbi, bcf and csi are binary; the vcf.gz is text compressed with gzip
    formats = {(str(d.format), str(d.compression_format) if d.compression_format else None) for d in result}
    assert formats == {(BIN, None), (TXT, GZIP)}
    vcf = next(d for d in result if d.compression_format)
    assert vcf.byte_size.value == "25455080"
    # Only the file with a number as extension is reported as unknown
    assert "EGAD00001005083 has 1 files with an unknown format" in caplog.text
    assert "'1664408722194' (1)" in caplog.text


def test_map_ega_to_healthri_dcat_distributions_puts_compression_in_compress_format(default_ega_dataset, ega_config):
    # Arrange
    default_ega_dataset["files"] = [
        {"accession_id": "EGAF00000000001", "filesize": 100, "extension": "vcf"},
        {"accession_id": "EGAF00000000002", "filesize": 200, "extension": "vcf.gz"},
        {"accession_id": "EGAF00000000003", "filesize": 300, "extension": "fastq.gz"},
    ]

    # Act
    result = map_ega_to_healthri_dcat_distributions(default_ega_dataset, ega_config)

    # Assert
    assert len(result) == 2
    sizes = {str(d.compression_format) if d.compression_format else None: d.byte_size.value for d in result}
    assert sizes == {None: "100", GZIP: "500"}
    assert {str(d.format) for d in result} == {TXT}

    compressed = next(d for d in result if d.compression_format)
    subject = URIRef("http://example.com/distribution")
    graph = compressed.to_graph(subject)
    assert (subject, DCAT.compressFormat, URIRef(GZIP)) in graph
    assert (subject, DCTERMS.format, URIRef(TXT)) in graph


def test_map_ega_to_healthri_dcat_distributions_does_not_warn_for_known_formats(
    default_ega_dataset, ega_config, caplog
):
    with caplog.at_level(logging.WARNING):
        map_ega_to_healthri_dcat_distributions(default_ega_dataset, ega_config)

    assert "unknown format" not in caplog.text


def test_map_ega_to_healthri_dcat_distributions_combines_files(default_ega_dataset, ega_config):
    # Act
    result = map_ega_to_healthri_dcat_distributions(default_ega_dataset, ega_config)

    # Assert
    distribution_config = ega_config["distribution"]
    assert len(result) == 1
    distribution = result[0]
    assert str(distribution.access_url) == "https://ega-archive.org/datasets/EGAD00001005083"
    assert distribution.byte_size.value == "3000"
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
    # Check the list, not a dict: a dict would hide two distributions for the same format
    assert len(result) == 2
    assert len({str(distribution.format) for distribution in result}) == 2
    sizes_per_format = {str(distribution.format): distribution.byte_size.value for distribution in result}
    assert sizes_per_format == {
        "http://publications.europa.eu/resource/authority/file-type/BIN": "3000",
        "http://publications.europa.eu/resource/authority/file-type/TXT": "500",
    }


def test_map_ega_to_healthri_dcat_distributions_raises_without_distribution_section(default_ega_dataset):
    """Files without a [distribution] section is a misconfiguration, which must not silently drop the Distributions."""
    with pytest.raises(ValueError, match=r"EGAD00001005083 has files, but .* no \[distribution\] section"):
        map_ega_to_healthri_dcat_distributions(default_ega_dataset, {})


def test_map_ega_to_healthri_dcat_distributions_needs_no_distribution_section_without_files(missing_ega_dataset):
    assert map_ega_to_healthri_dcat_distributions(missing_ega_dataset, {}) == []


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
    assert result.access_rights == AccessRights.non_public.value
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
    assert str(result.contact_point.hasEmail) == "mailto:dac@example.com"
    assert result.contact_point.formatted_name == contact_point_config["formatted_name"]
    assert result.contact_point.contact_page == [AnyHttpUrl("https://ega-archive.org/dacs/EGAC00001001143")]

    # EGA metadata does not distinguish creator from publisher, so the same agent is used for both.
    assert result.creator == [result.publisher]


def test_map_ega_to_healthri_dcat_dataset_without_dacs_has_no_contact_page(default_ega_dataset, ega_config):
    del default_ega_dataset["dacs"]

    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    assert result.contact_point.contact_page is None
    # Without a DAC contact, the configured email is used
    assert str(result.contact_point.hasEmail) == ega_config["dataset"]["contact_point"]["email"]
    assert result.qualified_attribution is None


def test_map_ega_to_healthri_dcat_dataset_refers_to_distributions(default_ega_dataset, ega_config):
    distribution_uri = URIRef("http://img2catalog.internal/distribution/EGAD00001005083/BIN")

    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config, [distribution_uri])

    assert [str(distribution) for distribution in result.distribution] == [str(distribution_uri)]


def test_map_ega_to_healthri_dcat_dataset_without_distributions(default_ega_dataset, ega_config):
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    assert result.distribution is None


def test_map_ega_to_healthri_dcat_dataset_maps_qualified_attribution(default_ega_dataset, ega_config):
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    assert len(result.qualified_attribution) == 1
    assert result.qualified_attribution[0].agent.identifier.value == "https://ega-archive.org/dacs/EGAC00001001143"


def test_map_ega_to_healthri_dcat_dataset_maps_ega_publications(default_ega_dataset, ega_config):
    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    assert result.is_referenced_by == [AnyHttpUrl("https://pubmed.ncbi.nlm.nih.gov/32526207/")]


def test_map_ega_to_healthri_dcat_dataset_leaves_optional_fields_empty(default_ega_dataset, ega_config):
    del default_ega_dataset["studies"]

    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    assert result.type is None
    assert result.personal_data is None
    assert result.language is None
    assert result.geographical_coverage is None
    assert result.status is None
    assert result.minimum_typical_age is None
    assert result.population_coverage is None
    assert result.is_referenced_by is None
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
    # Publications from the EGA studies come first, followed by the configured ones
    assert result.is_referenced_by == [
        AnyHttpUrl("https://pubmed.ncbi.nlm.nih.gov/32526207/"),
        *[AnyHttpUrl(url) for url in dataset_config["is_referenced_by"]],
    ]
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


def test_map_ega_to_healthri_dcat_catalog_accepts_toml_date(ega_catalog_config):
    """A bare TOML date (release_date = 2019-06-10, without quotes) is parsed as a date, not as a datetime"""
    ega_catalog_config["catalog"]["release_date"] = date(2019, 6, 10)

    result = map_ega_to_healthri_dcat_catalog(ega_catalog_config, [])

    assert result.release_date == datetime(2019, 6, 10)


def test_map_ega_to_healthri_dcat_catalog_raises_without_catalog_config(ega_config):
    with pytest.raises(KeyError):
        map_ega_to_healthri_dcat_catalog(ega_config, [])
