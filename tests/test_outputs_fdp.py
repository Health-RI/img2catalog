from unittest.mock import patch

import fairclient
import pytest
from fairclient.fdpclient import FDPClient
from rdflib import URIRef, DCTERMS

from img2catalog.outputs.fdp import FDPOutput


@patch("img2catalog.outputs.fdp.add_or_update_dataset")
@patch.object(FDPClient, "__init__", return_value=None)
def test_xnat_to_fdp_push(mock_fdp_client, mock_add_or_update_dataset, mock_dataset, config, empty_graph):
    """Tests of XNAT to RDF pushing happens even when errors happen"""
    # FIXME: Figure out what the goal is of this test

    mapped_objects = {
        'catalog': [],
        'dataset': [{
            'uri': URIRef("http://example.com/dataset"),
            'model_object': mock_dataset
        }]
    }

    fdp_output = FDPOutput(config, fdp="http://localhost",
                           fdp_username=None, fdp_password=None, catalog_uri=URIRef("http://example.com/catalog"))
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

    # xnat_to_FDP(None, config, URIRef("http://example.com/catalog"), None, None)
    mapped_objects = {
        'catalog': [],
        'dataset': [
            {
                'uri': URIRef("http://example.com/dataset1"),
                'model_object': mock_dataset
            },
            {
                'uri': URIRef("http://example.com/dataset2"),
                'model_object': mock_dataset
            }
        ]
    }

    fdp_output = FDPOutput(config, fdp="http://localhost",
                           fdp_username=None, fdp_password=None, catalog_uri=URIRef("http://example.com/catalog"))
    fdp_output.push_to_fdp(mapped_objects)

    assert mock_add_or_update_dataset.call_count == 2
    assert (
               URIRef("http://example.com/dataset2"),
               DCTERMS.isPartOf,
               URIRef("http://example.com/catalog"),
           ) in mock_add_or_update_dataset.call_args_list[1].args[0], "FDP catalog reference missing"

@patch.object(FDPClient, "__init__", return_value=None)
def test_fdp_catalog_uri_from_config(mock_fdp_client, config):
    fdp_output = FDPOutput(config, fdp="http://localhost", fdp_username=None, fdp_password=None)
    assert fdp_output.catalog_uri == URIRef('http://example.com')


@patch.object(FDPClient, "__init__", return_value=None)
def test_fdp_no_catalog_uri(mock_fdp_client):
    with pytest.raises(ValueError):
        _ = FDPOutput({}, fdp="http://localhost", fdp_username=None, fdp_password=None)
