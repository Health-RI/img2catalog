from unittest.mock import patch

import pytest
from fairclient.fdpclient import FDPClient
from rdflib import DCTERMS, URIRef

from img2catalog.outputs.fdp import FDPOutput


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

    with pytest.raises(ValueError, match="No catalog URI set to push to"):
        fdp_output.push_to_fdp(
            {"dataset": [{"uri": URIRef("http://example.com/dataset"), "model_object": mock_dataset}]}
        )
