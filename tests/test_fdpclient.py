from unittest.mock import MagicMock, patch

import pytest
import requests
from rdflib import Graph, URIRef
from rdflib.compare import to_isomorphic
from rdflib.namespace import DCAT, RDF

from img2catalog.fdpclient import (
    FDPClient,
    FDPSPARQLClient,
    add_or_update_dataset,
    remove_node_from_graph,
    rewrite_graph_subject,
)


@pytest.fixture
def fdp_client_mock(requests_mock):
    requests_mock.post("https://fdp.example.com/tokens", json={"token": "1234abcd"})
    requests_mock.put(
        "https://fdp.example.com/dataset/12345678/meta/state",
    )
    requests_mock.put(
        "https://fdp.example.com/dataset/12345678",
    )
    requests_mock.post(
        "https://fdp.example.com/dataset",
        status_code=201,
        headers={"Location": "https://fdp.example.com/dataset/12345678"},
        body=open(file="tests/references/fdp_dataset.ttl", mode="rb"),
    )
    requests_mock.post(
        "https://fdp.example.com/catalog",
        status_code=201,
        headers={"Location": "https://fdp.example.com/catalog/87654321"},
    )
    requests_mock.post(
        "https://fdp.example.com/distribution",
        status_code=201,
        headers={"Location": "https://fdp.example.com/distribution/abcdefgh"},
    )
    fdp_client = FDPClient("https://fdp.example.com", "user@example.com", "pass")

    return fdp_client


@pytest.fixture()
def empty_dataset_graph():
    g = Graph()
    g.add((URIRef("https://example.com/dataset"), RDF.type, DCAT.Dataset))

    return g


def test_fdp_login(requests_mock):
    requests_mock.post("https://fdp.example.com/tokens", json={"token": "1234abcd"})
    fdp_client = FDPClient("https://fdp.example.com", "user@example.com", "pass")

    assert requests_mock.call_count == 1
    assert requests_mock.last_request.json() == {"email": "user@example.com", "password": "pass"}
    assert fdp_client.get_headers() == {"Authorization": "Bearer 1234abcd", "Content-Type": "text/turtle"}


def test_fdp_login_trailing_slash(requests_mock):
    requests_mock.post("https://fdp.example.com/tokens", json={"token": "1234abcd"})
    fdp_client = FDPClient("https://fdp.example.com/", "user@example.com", "pass")

    assert requests_mock.call_count == 1
    assert requests_mock.last_request.json() == {"email": "user@example.com", "password": "pass"}
    assert fdp_client.get_headers() == {"Authorization": "Bearer 1234abcd", "Content-Type": "text/turtle"}


def test_fdp_login_error(requests_mock):
    requests_mock.post("http://fdp.example.com/tokens", status_code=403)

    with pytest.raises(requests.HTTPError):
        FDPClient("http://fdp.example.com", "wrong_email", "wrong_password")


def test_fdp_publish(requests_mock, fdp_client_mock: FDPClient):
    fdp_client_mock.publish_record("https://fdp.example.com/dataset/12345678")

    assert requests_mock.call_count == 2
    assert requests_mock.last_request.url == "https://fdp.example.com/dataset/12345678/meta/state"
    assert requests_mock.last_request.json() == {"current": "PUBLISHED"}


@pytest.mark.parametrize("metadata_type", ["dataset", "catalog", "distribution"])
def test_fdp_post_serialised(
    requests_mock,
    fdp_client_mock: FDPClient,
    metadata_type,
):
    requests_mock.post(f"https://fdp.example.com/{metadata_type}", text="")

    metadata = MagicMock(spec=Graph)
    metadata.serialize.return_value = ""
    # Ensure it's valid? Enforce lowercase?
    fdp_client_mock.post_serialized(metadata_type, metadata)

    assert requests_mock.last_request.url == f"https://fdp.example.com/{metadata_type}"
    assert requests_mock.last_request.headers["Content-Type"] == "text/turtle"
    assert requests_mock.last_request.headers["Authorization"] == "Bearer 1234abcd"
    assert requests_mock.last_request.method == "POST"
    metadata.serialize.assert_called_once_with(format="turtle")


def test_fdp_update_serialised(requests_mock, fdp_client_mock: FDPClient):
    requests_mock.put("http://fdp.example.com/dataset/test", text="")

    metadata = MagicMock(spec=Graph)
    metadata.serialize.return_value = ""
    # Ensure it's valid? Enforce lowercase?
    fdp_client_mock.update_serialized("http://fdp.example.com/dataset/test", metadata)

    assert requests_mock.last_request.url == "http://fdp.example.com/dataset/test"
    assert requests_mock.last_request.headers["Content-Type"] == "text/turtle"
    assert requests_mock.last_request.headers["Authorization"] == "Bearer 1234abcd"
    assert requests_mock.last_request.method == "PUT"
    metadata.serialize.assert_called_once_with(format="turtle")


# @pytest.mark.repeat(1)
# @patch("img2catalog.fdpclient.FDPClient.post_serialized")
# @patch("img2catalog.fdpclient.FDPClient.publish_record")
# publish_record, post_serialized, requests_mock
def test_fdp_create_and_publish(requests_mock, fdp_client_mock):
    empty_graph = Graph()

    assert fdp_client_mock.create_and_publish("dataset", empty_graph) == URIRef(
        "https://fdp.example.com/dataset/12345678"
    )
    # Test if dataset is pushed correctly
    assert requests_mock.request_history[-2].url == "https://fdp.example.com/dataset"
    assert requests_mock.request_history[-2].headers["Content-Type"] == "text/turtle"
    assert requests_mock.request_history[-2].method == "POST"

    # Test if dataset is actually published
    assert requests_mock.last_request.url == "https://fdp.example.com/dataset/12345678/meta/state"
    assert requests_mock.last_request.headers["Content-Type"] == "application/json"
    assert requests_mock.last_request.method == "PUT"
    assert requests_mock.last_request.json() == {"current": "PUBLISHED"}


def test_fdp_node_removal():
    reference_graph = Graph().parse("tests/references/empty_xnat.ttl")

    graph_to_modify = Graph().parse("tests/references/minimal_catalog_dataset.ttl")
    remove_node_from_graph(URIRef("https://example.com/dataset"), graph_to_modify)

    assert to_isomorphic(reference_graph) == to_isomorphic(graph_to_modify)


# These test cases are not the best. Better would be to emulate the actual endpoint
@patch("SPARQLWrapper.SPARQLWrapper.setQuery")
@patch("SPARQLWrapper.SPARQLWrapper.queryAndConvert")
def test_subject_query_success(queryAndConvert, setQuery):
    expected_decoded_json = {
        "head": {"vars": ["subject"]},
        "results": {
            "bindings": [
                {
                    "subject": {
                        "type": "uri",
                        "value": "http://example.com/dataset",
                    }
                }
            ]
        },
    }
    queryAndConvert.return_value = expected_decoded_json

    expected_query = """PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT *
WHERE {
    ?subject dcterms:identifier "https://example.com/dataset" .
    ?subject dcterms:isPartOf <https://example.com> .
}"""

    t = FDPSPARQLClient("https://example.com")

    assert t.find_subject("https://example.com/dataset", "https://example.com") == "http://example.com/dataset"
    setQuery.assert_called_with(expected_query)


@patch("SPARQLWrapper.SPARQLWrapper.queryAndConvert")
def test_subject_query_empty(queryAndConvert):
    expected_decoded_json = {
        "head": {"vars": ["subject"]},
        "results": {"bindings": []},
    }
    queryAndConvert.return_value = expected_decoded_json

    t = FDPSPARQLClient("https://example.com")

    assert t.find_subject("https://example.com/dataset", "https://example.com") is None


@patch("SPARQLWrapper.SPARQLWrapper.queryAndConvert")
def test_subject_query_multiple(queryAndConvert):
    expected_decoded_json = {
        "head": {"vars": ["subject"]},
        "results": {
            "bindings": [
                {
                    "subject": {
                        "type": "uri",
                        "value": "http://example.com/dataset1",
                    }
                },
                {
                    "subject": {
                        "type": "uri",
                        "value": "http://example.com/dataset2",
                    }
                },
            ]
        },
    }
    queryAndConvert.return_value = expected_decoded_json

    t = FDPSPARQLClient("https://example.com")
    with pytest.raises(ValueError):
        t.find_subject("https://example.com/dataset", "https://example.com")


@patch("SPARQLWrapper.SPARQLWrapper.queryAndConvert")
def test_subject_query_typeerror(queryAndConvert):
    expected_decoded_json = {
        "head": {"vars": ["subject"]},
        "results": {
            "bindings": [
                {
                    "subject": {
                        "type": "literal",
                        "value": "incorrect_result",
                    }
                }
            ]
        },
    }
    queryAndConvert.return_value = expected_decoded_json

    t = FDPSPARQLClient("https://example.com")
    with pytest.raises(TypeError):
        t.find_subject("https://example.com/dataset", "https://example.com")


# Not using the above FDP client here, easier to check if the related function calls in the client
# are made. We can assume those calls are correct as they are tested above
def test_dataset_updater_nomatch():
    sparqlclient = MagicMock(spec=FDPSPARQLClient)
    fdpclient = MagicMock(spec=FDPClient)
    metadata = Graph()
    dataset_identifier = "https://example.com/dataset"
    catalog_uri = "https://fdp.example.com/catalog/123"

    # No match found
    sparqlclient.find_subject.return_value = None

    add_or_update_dataset(metadata, fdpclient, dataset_identifier, catalog_uri, sparqlclient)

    sparqlclient.find_subject.assert_called_once_with(dataset_identifier, catalog_uri)
    fdpclient.create_and_publish.assert_called_once_with("dataset", metadata)
    fdpclient.update_serialized.assert_not_called()


def test_dataset_updater_match(empty_dataset_graph):
    sparqlclient = MagicMock(spec=FDPSPARQLClient)
    fdpclient = MagicMock(spec=FDPClient)
    metadata = empty_dataset_graph
    dataset_identifier = "https://example.com/dataset"
    catalog_uri = "https://fdp.example.com/catalog/123"

    subject_uri = "https://fdp.example.com/dataset/456"
    sparqlclient.find_subject.return_value = subject_uri

    add_or_update_dataset(metadata, fdpclient, dataset_identifier, catalog_uri, sparqlclient)

    sparqlclient.find_subject.assert_called_once_with(dataset_identifier, catalog_uri)
    fdpclient.create_and_publish.assert_not_called()
    fdpclient.update_serialized.assert_called_once_with(subject_uri, metadata)


def test_dataset_updater_invalid(empty_dataset_graph):
    sparqlclient = MagicMock(spec=FDPSPARQLClient)
    fdpclient = MagicMock(spec=FDPClient)
    metadata = empty_dataset_graph
    dataset_identifier = None
    catalog_uri = "https://fdp.example.com/catalog/123"

    add_or_update_dataset(metadata, fdpclient, dataset_identifier, catalog_uri, sparqlclient)

    fdpclient.create_and_publish.assert_called_once_with("dataset", metadata)
    sparqlclient.find_subject.assert_not_called()
    fdpclient.update_serialized.assert_not_called()


def test_subject_replacement():
    old_graph = Graph().parse(source="tests/references/valid_project.ttl")
    reference_graph = Graph().parse(source="tests/references/valid_project_subject_replaced.ttl")

    rewrite_graph_subject(
        old_graph, "http://localhost/data/archive/projects/test_img2catalog", "http://example.com/newsubject"
    )

    # print(new_graph.serialize())
    assert to_isomorphic(reference_graph) == to_isomorphic(old_graph)
