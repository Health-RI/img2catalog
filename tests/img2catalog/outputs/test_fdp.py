from unittest.mock import MagicMock, patch

import pytest
from fairclient.fdpclient import FDPClient
from rdflib import DCAT, DCTERMS, Graph, URIRef

from img2catalog.outputs.fdp import FDPOutput


@patch("img2catalog.outputs.fdp.add_or_update_dataset")
@patch.object(FDPClient, "__init__", return_value=None)
def test_xnat_to_fdp_push(mock_fdp_client, mock_add_or_update_dataset, mock_dataset, config, empty_graph):
    """Tests of XNAT to RDF pushing happens even when errors happen"""
    # FIXME: Figure out what the goal is of this test

    mapped_objects = {
        "catalog": [],
        "dataset": [{"uri": URIRef("http://example.com/dataset"), "model_object": mock_dataset}],
    }

    fdp_output = FDPOutput(
        config,
        fdp="http://localhost",
        fdp_username=None,
        fdp_password=None,
        catalog_uri=URIRef("http://example.com/catalog"),
    )
    fdp_output.push_to_fdp(mapped_objects)

    # Check if function is called and correct term added to Graph
    assert (
        URIRef("http://example.com/dataset"),
        DCTERMS.isPartOf,
        URIRef("http://example.com/catalog"),
    ) in mock_add_or_update_dataset.call_args.args[0], "FDP catalog reference missing"
    mock_add_or_update_dataset.assert_called_once()


@patch("img2catalog.outputs.fdp.add_or_update_dataset")
@patch.object(FDPClient, "__init__", return_value=None)
def test_xnat_to_fdp_push_error(mock_fdp_client, mock_add_or_update_dataset, mock_dataset, config, empty_graph):
    # FIXME: Figure out what the goal is of this test also
    mock_add_or_update_dataset.side_effect = [ValueError, None]

    mapped_objects = {
        "catalog": [],
        "dataset": [
            {"uri": URIRef("http://example.com/dataset1"), "model_object": mock_dataset},
            {"uri": URIRef("http://example.com/dataset2"), "model_object": mock_dataset},
        ],
    }

    fdp_output = FDPOutput(
        config,
        fdp="http://localhost",
        fdp_username=None,
        fdp_password=None,
        catalog_uri=URIRef("http://example.com/catalog"),
    )
    fdp_output.push_to_fdp(mapped_objects)

    assert mock_add_or_update_dataset.call_count == 2
    assert (
        URIRef("http://example.com/dataset2"),
        DCTERMS.isPartOf,
        URIRef("http://example.com/catalog"),
    ) in mock_add_or_update_dataset.call_args_list[1].args[0], "FDP catalog reference missing"


FILE_TYPE_BINARY = URIRef("http://publications.europa.eu/resource/authority/file-type/BIN")


def _distribution_objects():
    dataset_uri = URIRef("http://example.com/dataset")
    distribution_uri = URIRef("http://example.com/distribution/BIN")
    distribution = MagicMock()
    distribution.format = FILE_TYPE_BINARY
    distribution.to_graph.side_effect = lambda subject: Graph().add((subject, DCTERMS.format, FILE_TYPE_BINARY))
    return dataset_uri, {"uri": distribution_uri, "model_object": distribution, "dataset_uri": dataset_uri}


def _sparql_bindings(*subjects):
    return {"results": {"bindings": [{"subject": {"type": "uri", "value": subject}} for subject in subjects]}}


@patch.object(FDPClient, "create_and_publish")
@patch("img2catalog.outputs.fdp.add_or_update_dataset")
@patch.object(FDPClient, "__init__", return_value=None)
def test_fdp_push_creates_distribution(
    mock_fdp_client, mock_add_or_update_dataset, mock_create_and_publish, mock_dataset, config
):
    dataset_uri, distribution = _distribution_objects()
    fdp_dataset_uri = URIRef("http://fdp.example.com/dataset/1")
    mock_add_or_update_dataset.return_value = fdp_dataset_uri
    mock_dataset.distribution = [distribution["uri"]]

    fdp_output = FDPOutput(
        config, fdp="http://localhost", fdp_username=None, fdp_password=None, catalog_uri="http://example.com/catalog"
    )
    fdp_output.push_to_fdp(
        {"dataset": [{"uri": dataset_uri, "model_object": mock_dataset}], "distribution": [distribution]}
    )

    # The FDP links the Distribution to the Dataset itself, so the internal link is not pushed
    dataset_graph = mock_add_or_update_dataset.call_args.args[0]
    assert (dataset_uri, DCAT.distribution, None) not in dataset_graph

    resource_type, distribution_graph = mock_create_and_publish.call_args.args
    assert resource_type == "distribution"
    assert (distribution["uri"], DCTERMS.isPartOf, fdp_dataset_uri) in distribution_graph


@patch.object(FDPClient, "create_and_publish")
@patch.object(FDPClient, "update_serialized")
@patch("img2catalog.outputs.fdp.add_or_update_dataset")
@patch.object(FDPClient, "__init__", return_value=None)
def test_fdp_push_updates_existing_distribution(
    mock_fdp_client, mock_add_or_update_dataset, mock_update_serialized, mock_create_and_publish, mock_dataset, config
):
    dataset_uri, distribution = _distribution_objects()
    fdp_dataset_uri = "http://fdp.example.com/dataset/1"
    fdp_distribution_uri = "http://fdp.example.com/distribution/1"
    # An updated dataset does not return its FDP URI
    mock_add_or_update_dataset.return_value = MagicMock()

    fdp_output = FDPOutput(
        config,
        fdp="http://localhost",
        fdp_username=None,
        fdp_password=None,
        catalog_uri="http://example.com/catalog",
        sparql="http://localhost/sparql",
    )
    fdp_output.sparqlclient.find_subject = MagicMock(return_value=fdp_dataset_uri)
    fdp_output.sparqlclient.sparql = MagicMock()
    fdp_output.sparqlclient.sparql.queryAndConvert.return_value = _sparql_bindings(fdp_distribution_uri)

    fdp_output.push_to_fdp(
        {"dataset": [{"uri": dataset_uri, "model_object": mock_dataset}], "distribution": [distribution]}
    )

    mock_create_and_publish.assert_not_called()
    updated_uri, distribution_graph = mock_update_serialized.call_args.args
    assert updated_uri == fdp_distribution_uri
    assert (URIRef(fdp_distribution_uri), DCTERMS.isPartOf, URIRef(fdp_dataset_uri)) in distribution_graph
    assert (distribution["uri"], None, None) not in distribution_graph


@patch.object(FDPClient, "__init__", return_value=None)
def test_fdp_find_distribution_subject_raises_on_multiple(mock_fdp_client, config):
    fdp_output = FDPOutput(
        config, fdp="http://localhost", fdp_username=None, fdp_password=None, sparql="http://localhost/sparql"
    )
    fdp_output.sparqlclient.sparql = MagicMock()
    fdp_output.sparqlclient.sparql.queryAndConvert.return_value = _sparql_bindings(
        "http://fdp.example.com/distribution/1", "http://fdp.example.com/distribution/2"
    )

    with pytest.raises(ValueError, match="More than one distribution"):
        fdp_output._find_distribution_subject(URIRef("http://fdp.example.com/dataset/1"), FILE_TYPE_BINARY)


@patch.object(FDPClient, "__init__", return_value=None)
def test_fdp_catalog_uri_from_config(mock_fdp_client, config):
    fdp_output = FDPOutput(config, fdp="http://localhost", fdp_username=None, fdp_password=None)
    assert fdp_output.catalog_uri == URIRef("http://example.com")


@patch.object(FDPClient, "__init__", return_value=None)
def test_fdp_no_catalog_uri(mock_fdp_client):
    with pytest.raises(ValueError, match="No catalog URI set to push to"):
        _ = FDPOutput({}, fdp="http://localhost", fdp_username=None, fdp_password=None)
