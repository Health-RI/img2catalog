"""Empty values in EGA metadata or configuration are left out, instead of being mapped as if they have content."""

import logging
import re

import pytest
from rdflib import RDF, BNode, Literal, URIRef

from img2catalog.mappings.ega import (
    MissingEGAValueError,
    _is_empty,
    _text,
    get_byte_size,
    get_contact_email,
    get_contact_name,
    get_contact_page,
    get_description,
    get_is_referenced_by,
    get_keyword,
    get_qualified_attribution,
    get_release_date,
    get_title,
    map_ega_to_healthri_dcat_catalog,
    map_ega_to_healthri_dcat_dataset,
    map_ega_to_healthri_dcat_distributions,
)
from img2catalog.outputs.rdf import RDFOutput

DATASET_URI = URIRef("http://img2catalog.internal/dataset/EGAD00001005083")
DISTRIBUTION_URI = URIRef("http://img2catalog.internal/distribution/EGAD00001005083/BIN")
CATALOG_URI = URIRef("http://img2catalog.internal/catalog/ega")


@pytest.fixture
def empty_ega_dataset(default_ega_dataset):
    """An EGA dataset in which every optional value is empty, null or blank."""
    default_ega_dataset.update(
        {
            "technologies": ["Illumina HiSeq 2000", "", "   ", None],
            "num_samples": None,
            "released_date": "",
            "studies": [{"accession_id": "EGAS1", "pubmed_ids": ["", None]}, {"accession_id": "EGAS2"}],
        }
    )
    default_ega_dataset["dacs"][0]["contacts"] = [
        {"is_main": True, "email": "", "first_name": None, "surname": "Doe"},
        {"is_main": True, "email": "nameless@example.com", "first_name": None, "surname": " "},
    ]
    default_ega_dataset["dacs"].append(
        {"accession_id": None, "contacts": [{"is_main": True, "first_name": "No", "surname": "Accession"}]}
    )
    default_ega_dataset["files"] = [
        {"accession_id": "EGAF1", "filesize": None, "extension": "bam"},
        {"accession_id": "EGAF2", "filesize": 1000, "extension": "bam"},
    ]
    return default_ega_dataset


@pytest.fixture
def empty_values_config(ega_config):
    """A configuration in which every optional value is empty or blank."""
    ega_config["dataset"].update(
        {
            "keyword": ["", "   "],
            "population_coverage": "  ",
            "health_theme": [],
            "spatial": [""],
            "is_referenced_by": [""],
            "legal_basis": None,
            "qualified_attribution": {"role": ""},
        }
    )
    ega_config["dataset"]["publisher"]["publisher_type"] = ""
    ega_config["distribution"]["language"] = [""]
    ega_config["catalog"] = {
        "title": "Example EGA catalog",
        "description": "This is an example EGA catalog description",
        "spatial": [],
        "language": [""],
        "release_date": "",
        "contact_point": {
            "formatted_name": "Example Data Management office",
            "email": "mailto:datamanager@example.com",
        },
    }
    return ega_config


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, True),
        ("", True),
        ("   ", True),
        ([], True),
        ([None, "", " "], True),
        ({}, True),
        ({"role": ""}, True),
        ("value", False),
        (["", "value"], False),
        ({"role": "", "name": "value"}, False),
        (0, False),
        (False, False),
    ],
)
def test_is_empty(value, expected):
    assert _is_empty(value) is expected


def test_get_keyword_skips_empty_technologies(empty_ega_dataset):
    assert [keyword.value for keyword in get_keyword(empty_ega_dataset)] == ["Illumina HiSeq 2000"]


def test_get_keyword_handles_null_technologies(default_ega_dataset):
    default_ega_dataset["technologies"] = None

    assert get_keyword(default_ega_dataset) == []


@pytest.mark.parametrize("get_field", [get_title, get_description])
@pytest.mark.parametrize("value", ["", "   ", None])
def test_mandatory_text_raises_when_empty(default_ega_dataset, get_field, value):
    default_ega_dataset["title"] = value
    default_ega_dataset["description"] = value

    with pytest.raises(MissingEGAValueError, match="has no"):
        get_field(default_ega_dataset)


def test_get_release_date_returns_none_when_blank(empty_ega_dataset):
    assert get_release_date(empty_ega_dataset) is None


@pytest.mark.parametrize(
    ("contact", "expected"),
    [
        ({"first_name": "John", "surname": "Doe"}, "John Doe"),
        ({"first_name": None, "surname": "Doe"}, "Doe"),
        ({"first_name": " John ", "surname": ""}, "John"),
        ({"surname": "Doe"}, "Doe"),
        ({"first_name": None, "surname": " "}, None),
        ({}, None),
    ],
)
def test_get_contact_name_leaves_out_empty_parts(contact, expected):
    assert get_contact_name(contact) == expected


def test_get_contact_email_skips_blank_email(empty_ega_dataset):
    # The first main contact has a blank email, so the email of the second one is used
    assert get_contact_email(empty_ega_dataset) == "mailto:nameless@example.com"


def test_get_qualified_attribution_skips_empty_values(empty_ega_dataset, empty_values_config):
    result = get_qualified_attribution(empty_ega_dataset, empty_values_config["dataset"])

    # The contact without a name is left out, the blank email and role are not mapped
    assert len(result) == 1
    assert [name.value for name in result[0].agent.name] == ["Doe"]
    assert result[0].agent.mbox is None
    assert result[0].role is None


def test_get_is_referenced_by_skips_empty_pubmed_ids(empty_ega_dataset):
    assert get_is_referenced_by(empty_ega_dataset) == []


def test_get_byte_size_sums_known_sizes(caplog):
    with caplog.at_level(logging.WARNING):
        result = get_byte_size([{"filesize": None}, {"filesize": 1000}, {"filesize": 0}])

    assert result.value == "1000"
    assert "Size of 1 of 3 files is unknown" in caplog.text


def test_get_byte_size_returns_none_without_known_sizes():
    assert get_byte_size([{"filesize": None}, {}]) is None


def test_map_distributions_skips_distribution_without_known_size(default_ega_dataset, ega_config, caplog):
    default_ega_dataset["files"] = [
        {"accession_id": "EGAF1", "filesize": None, "extension": "bam"},
        {"accession_id": "EGAF2", "filesize": 500, "extension": "vcf"},
    ]

    with caplog.at_level(logging.WARNING):
        result = map_ega_to_healthri_dcat_distributions(default_ega_dataset, ega_config)

    assert [str(distribution.format) for distribution in result] == [
        "http://publications.europa.eu/resource/authority/file-type/TXT"
    ]
    assert "Skipping BIN Distribution of EGA dataset EGAD00001005083" in caplog.text


def test_map_distributions_leaves_out_empty_config_values(empty_ega_dataset, empty_values_config):
    result = map_ega_to_healthri_dcat_distributions(empty_ega_dataset, empty_values_config)

    assert len(result) == 1
    assert result[0].byte_size.value == "1000"
    assert result[0].language is None
    assert result[0].release_date is None


def test_map_dataset_leaves_out_empty_values(empty_ega_dataset, empty_values_config):
    result = map_ega_to_healthri_dcat_dataset(empty_ega_dataset, empty_values_config, [])

    assert [keyword.value for keyword in result.keyword] == ["Illumina HiSeq 2000"]
    assert result.population_coverage is None
    assert result.health_theme is None
    assert result.geographical_coverage is None
    assert result.is_referenced_by is None
    assert result.legal_basis is None
    assert result.number_of_records is None
    assert result.release_date is None
    assert result.distribution is None
    assert result.publisher.publisher_type is None
    assert len(result.qualified_attribution) == 1


def test_map_catalog_leaves_out_empty_values(empty_values_config):
    result = map_ega_to_healthri_dcat_catalog(empty_values_config, [DATASET_URI])

    assert result.geographical_coverage is None
    assert result.language is None
    assert result.release_date is None


def test_text_refuses_lists_and_dicts():
    with pytest.raises(TypeError, match="Expected a single text value"):
        _text(["a", None])
    with pytest.raises(TypeError, match="Expected a single text value"):
        _text({"en": "adults"})


def test_map_dataset_refuses_list_for_single_text_config(default_ega_dataset, ega_config):
    # Instead of showing it as the text "['adults', None]"
    ega_config["dataset"]["population_coverage"] = ["adults", None]

    with pytest.raises(TypeError, match="Expected a single text value"):
        map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)


@pytest.mark.parametrize("key", ["dacs", "files", "studies", "technologies"])
def test_map_dataset_handles_null_lists(default_ega_dataset, ega_config, key):
    default_ega_dataset[key] = None

    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    assert result.title[0].value == default_ega_dataset["title"]
    assert map_ega_to_healthri_dcat_distributions(default_ega_dataset, ega_config) is not None


def test_get_contact_name_leaves_out_null_surname():
    """EGA has DAC contacts with only a name in first_name and a null surname, e.g. EGAD00001001500."""
    assert get_contact_name({"first_name": "Blueprint DAC", "surname": None}) == "Blueprint DAC"


def test_dac_without_accession_id_is_left_out(default_ega_dataset, ega_config):
    default_ega_dataset["dacs"][0]["accession_id"] = None

    assert get_contact_page(default_ega_dataset) == []
    assert get_qualified_attribution(default_ega_dataset, ega_config["dataset"]) == []


def test_map_dataset_falls_back_to_configured_email_when_dac_email_is_blank(default_ega_dataset, ega_config):
    default_ega_dataset["dacs"][0]["contacts"][0]["email"] = "  "

    result = map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)

    assert str(result.contact_point.hasEmail) == ega_config["dataset"]["contact_point"]["email"]


def test_get_byte_size_treats_blank_size_as_unknown():
    assert get_byte_size([{"filesize": ""}, {"filesize": "1000"}]).value == "1000"


@pytest.mark.parametrize("key", ["name", "identifier"])
def test_map_dataset_refuses_empty_mandatory_publisher_config(default_ega_dataset, ega_config, key):
    ega_config["dataset"]["publisher"][key] = [""]

    with pytest.raises(ValueError, match=f"'{key}' is mandatory, but empty"):
        map_ega_to_healthri_dcat_dataset(default_ega_dataset, ega_config)


@pytest.mark.parametrize("key", ["title", "description"])
def test_map_catalog_refuses_empty_mandatory_config(empty_values_config, key):
    empty_values_config["catalog"][key] = " "

    with pytest.raises(ValueError, match=f"'{key}' is mandatory, but empty"):
        map_ega_to_healthri_dcat_catalog(empty_values_config, [DATASET_URI])


def _empty_values_in_graph(graph):
    """Find the values in a graph that are shown as having content while they are empty."""
    empty_values = []
    for _subject, predicate, value in graph:
        text = str(value)
        if isinstance(value, Literal) and (
            not text.strip() or re.search(r"\bNone\b", text) or re.fullmatch(r"\s*[\[{].*[\]}]\s*", text)
        ):
            # Blank text, "None" text, or a list or dict shown as text
            empty_values.append((predicate, value))
        if isinstance(value, URIRef) and (not text.strip() or "/None" in text or re.search(r"[^:]//", text)):
            # A URL built from an empty or None part
            empty_values.append((predicate, value))
        # A class without any property besides its type has no content
        if isinstance(value, BNode) and set(graph.predicates(value)) <= {RDF.type}:
            empty_values.append((predicate, "empty class"))
    return empty_values


def test_rdf_output_has_no_empty_values(empty_ega_dataset, empty_values_config):
    """Only values that are set are displayed, in all mapped classes and their nested classes."""
    # Arrange
    distributions = map_ega_to_healthri_dcat_distributions(empty_ega_dataset, empty_values_config)
    dataset = map_ega_to_healthri_dcat_dataset(empty_ega_dataset, empty_values_config, [DISTRIBUTION_URI])
    catalog = map_ega_to_healthri_dcat_catalog(empty_values_config, [DATASET_URI])
    rdf_output = RDFOutput(empty_values_config)

    # Act
    rdf_output.create_graph(
        {
            "catalog": [{"uri": CATALOG_URI, "model_object": catalog}],
            "dataset": [{"uri": DATASET_URI, "model_object": dataset}],
            "distribution": [{"uri": DISTRIBUTION_URI, "model_object": distributions[0]}],
        }
    )

    # Assert
    assert _empty_values_in_graph(rdf_output.graph) == []
    assert len(rdf_output.graph) > 0
