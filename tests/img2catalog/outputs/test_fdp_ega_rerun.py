"""Rerunning the EGA to FDP push updates the datasets in the FDP, instead of adding them again."""

import json
import logging
from unittest.mock import Mock, patch

import pytest
import requests
from fairclient.fdpclient import FDPClient
from fairclient.sparqlclient import FDPSPARQLClient
from rdflib import DCAT, DCTERMS, Graph, Literal, URIRef
from sempyro import LiteralField

from img2catalog.mappings.ega import map_ega_to_healthri_dcat_dataset
from img2catalog.outputs.fdp import FDPOutput, FDPPushError, get_identifier_value, remove_internal_distribution_links

from .fake_fdp import FakeSPARQLEndpoint, connect_fake_fdp

CATALOG_URI = URIRef("http://fdp.example.com/catalog/ega")
DATASET_URI = URIRef("http://img2catalog.internal/dataset/EGAD00001005083")

# The SPARQL parser of rdflib, used by the fake FDP, uses deprecated pyparsing functions
pytestmark = [
    pytest.mark.filterwarnings(r"ignore::DeprecationWarning:rdflib.plugins.sparql"),
    pytest.mark.filterwarnings(r"ignore::DeprecationWarning:pyparsing"),
]


@pytest.fixture
def fdp_output(config):
    with patch.object(FDPClient, "__init__", return_value=None):
        fdp_output = FDPOutput(
            config, fdp="http://fdp.example.com", fdp_username="user", fdp_password="pass", catalog_uri=CATALOG_URI
        )
    connect_fake_fdp(fdp_output)
    return fdp_output


def _mapped_objects(ega_dataset, config):
    """Map an EGA dataset like the CLI does, linking it to its Distribution by an internal URI."""
    distribution_uri = URIRef(f"http://img2catalog.internal/distribution/{ega_dataset['accession_id']}/BIN")
    dataset = map_ega_to_healthri_dcat_dataset(ega_dataset, config, [distribution_uri])
    return {"dataset": [{"uri": DATASET_URI, "model_object": dataset}]}


@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        (
            LiteralField(value="https://ega-archive.org/datasets/EGAD00001005083"),
            "https://ega-archive.org/datasets/EGAD00001005083",
        ),
        ("https://example.com/img-123", "https://example.com/img-123"),
        (None, None),
    ],
)
def test_get_identifier_value(identifier, expected):
    assert get_identifier_value(identifier) == expected


def test_rerun_updates_ega_dataset_in_fdp(fdp_output, default_ega_dataset, ega_config):
    # Arrange: the dataset was pushed to the FDP by an earlier run
    fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))
    assert list(fdp_output.fdpclient.datasets) == [URIRef("http://fdp.example.com/dataset/1")]

    # Act: the dataset changed in EGA and the script is run again
    default_ega_dataset["title"] = "Updated title"
    fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))

    # Assert: the same FDP dataset is updated, instead of a second one being added
    assert list(fdp_output.fdpclient.datasets) == [URIRef("http://fdp.example.com/dataset/1")]
    updated = fdp_output.fdpclient.datasets[URIRef("http://fdp.example.com/dataset/1")]
    assert set(updated.objects(URIRef("http://fdp.example.com/dataset/1"), DCTERMS.title)) == {Literal("Updated title")}
    assert (URIRef("http://fdp.example.com/dataset/1"), DCTERMS.isPartOf, CATALOG_URI) in updated
    # No link to the Distribution, which is not pushed, and no internal URI is left in the FDP
    assert not any("img2catalog.internal" in str(term) for triple in updated for term in triple)
    # The FDP is queried with the plain EGA identifier, not the representation of the identifier object
    assert (
        'dcterms:identifier "https://ega-archive.org/datasets/EGAD00001005083"'
        in (fdp_output.sparqlclient.sparql.queries[-1])
    )


def test_rerun_keeps_datasets_apart(fdp_output, default_ega_dataset, ega_config):

    def mapped_objects(title, other_title):
        dataset = {**default_ega_dataset, "title": title}
        other_dataset = {**default_ega_dataset, "accession_id": "EGAD00001005084", "title": other_title}
        objects = _mapped_objects(dataset, ega_config)
        objects["dataset"] += _mapped_objects(other_dataset, ega_config)["dataset"]
        objects["dataset"][1]["uri"] = URIRef("http://img2catalog.internal/dataset/EGAD00001005084")
        return objects

    def titles():
        """Title of each FDP dataset, by the FDP URI of the dataset."""
        return {uri: str(graph.value(uri, DCTERMS.title)) for uri, graph in fdp_output.fdpclient.datasets.items()}

    # Act: push, change both datasets, and push again
    fdp_output.push_to_fdp(mapped_objects("First", "Second"))
    assert sorted(titles().values()) == ["First", "Second"]
    first_uris = set(fdp_output.fdpclient.datasets)
    fdp_output.push_to_fdp(mapped_objects("First updated", "Second updated"))

    # Assert: each dataset was found and updated by itself, and none was added
    assert set(fdp_output.fdpclient.datasets) == first_uris
    assert sorted(titles().values()) == ["First updated", "Second updated"]


def test_push_without_sparql_warns_that_datasets_are_not_updated(fdp_output, default_ega_dataset, ega_config, caplog):
    fdp_output.sparqlclient = None

    with caplog.at_level(logging.WARNING):
        fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))

    assert "No SPARQL endpoint set" in caplog.text
    assert len(fdp_output.fdpclient.datasets) == 1


def test_rerun_with_duplicates_in_fdp_warns_with_identifier(fdp_output, default_ega_dataset, ega_config, caplog):
    """Duplicates left by earlier pushes are reported, instead of a third copy being added."""
    fdp_output.sparqlclient = None
    fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))
    fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))
    fdp_output.sparqlclient = FDPSPARQLClient("http://fdp.example.com/sparql")
    fdp_output.sparqlclient.sparql = FakeSPARQLEndpoint(fdp_output.fdpclient)

    mapped_objects = _mapped_objects(default_ega_dataset, ega_config)

    with caplog.at_level(logging.WARNING), pytest.raises(FDPPushError, match="1 of 1 datasets could not be pushed"):
        fdp_output.push_to_fdp(mapped_objects)

    assert len(fdp_output.fdpclient.datasets) == 2
    assert (
        "Error pushing dataset https://ega-archive.org/datasets/EGAD00001005083 to FDP: "
        "More than one result for SPARQL query. Remove the duplicate datasets"
    ) in caplog.text


def test_remove_internal_distribution_links_keeps_actual_distributions():
    """Distributions with an actual URI, e.g. entered in an XNAT custom form, are still linked."""
    graph = Graph()
    actual_distribution = URIRef("https://example.com/distribution/1")
    internal_distribution = URIRef("http://img2catalog.internal/distribution/EGAD00001005083/BIN")
    graph.add((DATASET_URI, DCAT.distribution, actual_distribution))
    graph.add((DATASET_URI, DCAT.distribution, internal_distribution))

    remove_internal_distribution_links(graph, DATASET_URI)

    assert set(graph.objects(DATASET_URI, DCAT.distribution)) == {actual_distribution}


def test_rerun_keeps_published_dataset_published(fdp_output, default_ega_dataset, ega_config, caplog):
    fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))

    with caplog.at_level(logging.INFO):
        fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))

    assert fdp_output.fdpclient.states == {URIRef("http://fdp.example.com/dataset/1"): "PUBLISHED"}
    # Not published again, which the FDP would refuse
    assert "Publishing dataset" not in caplog.text
    assert "Error pushing dataset" not in caplog.text


def test_rerun_publishes_dataset_that_stayed_draft(fdp_output, default_ega_dataset, ega_config, caplog):
    """When publishing failed at creation, the dataset is a draft in the FDP, which a rerun publishes."""
    # Arrange
    fdp_output.fdpclient.publish_fails = True
    mapped_objects = _mapped_objects(default_ega_dataset, ega_config)
    with pytest.raises(FDPPushError, match="could not be pushed"):
        fdp_output.push_to_fdp(mapped_objects)
    assert fdp_output.fdpclient.states == {URIRef("http://fdp.example.com/dataset/1"): "DRAFT"}
    fdp_output.fdpclient.publish_fails = False

    # Act
    with caplog.at_level(logging.INFO):
        fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))

    # Assert
    assert fdp_output.fdpclient.states == {URIRef("http://fdp.example.com/dataset/1"): "PUBLISHED"}
    assert "Publishing http://fdp.example.com/dataset/1, which was still a draft" in caplog.text


def test_rerun_updates_dataset_when_state_cannot_be_checked(fdp_output, default_ega_dataset, ega_config, caplog):
    fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))
    default_ega_dataset["title"] = "Updated title"

    mapped_objects = _mapped_objects(default_ega_dataset, ega_config)
    unreachable = patch.object(fdp_output.fdpclient, "get", side_effect=requests.ConnectionError("timeout"))
    with unreachable, caplog.at_level(logging.WARNING), pytest.raises(FDPPushError, match="could not be pushed"):
        fdp_output.push_to_fdp(mapped_objects)

    # The update itself went through, but the push is reported as failed, as the dataset may have stayed a draft
    updated = fdp_output.fdpclient.datasets[URIRef("http://fdp.example.com/dataset/1")]
    assert Literal("Updated title") in set(updated.objects(None, DCTERMS.title))
    assert "Could not check if http://fdp.example.com/dataset/1 is published in the FDP" in caplog.text


def test_failed_push_without_duplicates_gets_no_duplicate_hint(fdp_output, default_ega_dataset, ega_config, caplog):
    """A ValueError that is not about duplicates, like a SPARQL endpoint answering with a web page, is not solved by
    removing datasets from the FDP, so the log does not say so."""
    unreadable = patch.object(
        fdp_output.sparqlclient.sparql,
        "queryAndConvert",
        side_effect=json.JSONDecodeError("Expecting value", "<html>", 0),
    )

    with unreadable, caplog.at_level(logging.WARNING), pytest.raises(FDPPushError, match="1 of 1 datasets"):
        fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))

    assert (
        "Error pushing dataset https://ega-archive.org/datasets/EGAD00001005083 to FDP: Expecting value" in caplog.text
    )
    assert "Remove the duplicate datasets" not in caplog.text
    assert fdp_output.fdpclient.datasets == {}


def test_rerun_reports_failure_when_publishing_a_draft_fails_again(fdp_output, default_ega_dataset, ega_config, caplog):
    """When the FDP is still unreachable at the rerun, the dataset stays a draft and the push is reported as failed."""
    # Arrange: the dataset was created, but not published
    fdp_output.fdpclient.publish_fails = True
    with pytest.raises(FDPPushError):
        fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))

    # Act
    with caplog.at_level(logging.WARNING), pytest.raises(FDPPushError, match="1 of 1 datasets could not be pushed"):
        fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))

    # Assert: still the same dataset, and still a draft
    assert fdp_output.fdpclient.states == {URIRef("http://fdp.example.com/dataset/1"): "DRAFT"}
    assert (
        "Error pushing dataset https://ega-archive.org/datasets/EGAD00001005083 to FDP: FDP not reachable"
        in caplog.text
    )


def test_rerun_reports_failure_when_state_check_is_refused(fdp_output, default_ega_dataset, ega_config, caplog):
    fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))
    refused = Mock(raise_for_status=Mock(side_effect=requests.HTTPError("403 Forbidden")))

    state_check_refused = patch.object(fdp_output.fdpclient, "get", return_value=refused)
    with state_check_refused, caplog.at_level(logging.WARNING), pytest.raises(
        FDPPushError, match="could not be pushed"
    ):
        fdp_output.push_to_fdp(_mapped_objects(default_ega_dataset, ega_config))

    assert (
        "Could not check if http://fdp.example.com/dataset/1 is published in the FDP: 403 Forbidden"
        in caplog.text
    )
