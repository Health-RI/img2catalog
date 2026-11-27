from unittest.mock import MagicMock, patch

import pytest
from fairclient.fdpclient import FDPClient
from rdflib import DCTERMS, Graph, URIRef

from img2catalog.outputs.fdp import FDPCatalogError, FDPOutput, FDPPushError, escape_sparql_string


@patch.object(FDPOutput, "push_record", return_value=URIRef("http://fdp.example.com/dataset/1"))
@patch.object(FDPClient, "__init__", return_value=None)
def test_xnat_to_fdp_push(mock_fdp_client, mock_push_record, mock_dataset, config, empty_graph):
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
    ) in mock_push_record.call_args.args[1], "FDP catalog reference missing"
    mock_push_record.assert_called_once()


@patch.object(FDPOutput, "push_record")
@patch.object(FDPClient, "__init__", return_value=None)
def test_xnat_to_fdp_push_error(mock_fdp_client, mock_push_record, mock_dataset, config, empty_graph):
    """An error pushing one dataset does not stop pushing the others"""
    mock_push_record.side_effect = [ValueError, URIRef("http://fdp.example.com/dataset/2")]

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
    # The other dataset is still pushed, and the failed one makes the push fail afterwards
    with pytest.raises(FDPPushError, match="1 record"):
        fdp_output.push_to_fdp(mapped_objects)

    assert mock_push_record.call_count == 2
    assert (
        URIRef("http://example.com/dataset2"),
        DCTERMS.isPartOf,
        URIRef("http://example.com/catalog"),
    ) in mock_push_record.call_args_list[1].args[1], "FDP catalog reference missing"


@patch.object(FDPClient, "__init__", return_value=None)
def test_fdp_catalog_uri_from_config(mock_fdp_client, config):
    fdp_output = FDPOutput(config, fdp="http://localhost", fdp_username=None, fdp_password=None)
    assert fdp_output.catalog_uri == URIRef("http://example.com")


@patch.object(FDPClient, "__init__", return_value=None)
def test_fdp_no_catalog_uri(mock_fdp_client, mock_dataset):
    """Without a catalog URI and without a Catalog in the mapping, there is no catalog to push the datasets to"""
    fdp_output = FDPOutput({}, fdp="http://localhost", fdp_username=None, fdp_password=None)
    mapped_objects = {"dataset": [{"uri": URIRef("http://example.com/dataset"), "model_object": mock_dataset}]}

    with pytest.raises(FDPCatalogError, match="No catalog URI set to push to"):
        fdp_output.push_to_fdp(mapped_objects)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://example.com/ds-1", "https://example.com/ds-1"),
        ('a" . ?s ?p ?o', 'a\\" . ?s ?p ?o'),
        ("back\\slash", "back\\\\slash"),
        ("two\nlines\r\tand tab", "two\\nlines\\r\\tand tab"),
    ],
)
def test_escape_sparql_string(text, expected):
    assert escape_sparql_string(text) == expected


@patch.object(FDPClient, "__init__", return_value=None)
def test_push_dataset_looks_up_an_escaped_identifier(mock_fdp_client):
    """An identifier from the input must not be able to end the string literal in the query for the dataset."""
    fdp_output = FDPOutput({}, fdp="http://localhost", fdp_username=None, fdp_password=None)
    fdp_output.sparqlclient = MagicMock()
    fdp_output.sparqlclient.find_subject.return_value = None
    fdp_output.push_record = MagicMock()
    model_object = MagicMock(identifier='ds-1" . ?subject ?p ?o #')
    model_object.to_graph.return_value = Graph()
    dataset = {"uri": URIRef("http://img2catalog.internal/dataset/1"), "model_object": model_object}
    catalog = URIRef("http://example.com/catalog")

    fdp_output.push_dataset(dataset, catalog)

    fdp_output.sparqlclient.find_subject.assert_called_once_with('ds-1\\" . ?subject ?p ?o #', catalog)
