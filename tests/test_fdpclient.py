from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
from rdflib import Graph, URIRef

from img2catalog.fdpclient import FDPClient


@pytest.fixture
def fdp_client_mock(requests_mock):
    requests_mock.post("http://fdp.example.com/tokens", json={"token": "1234abcd"})
    fdp_client = FDPClient("http://fdp.example.com", "user@example.com", "pass")

    return fdp_client


def test_fdp_login(requests_mock):
    requests_mock.post("http://fdp.example.com/tokens", json={"token": "1234abcd"})

    fdp_client = FDPClient("http://fdp.example.com", "user@example.com", "pass")

    assert requests_mock.call_count == 1
    assert requests_mock.last_request.json() == {"email": "user@example.com", "password": "pass"}
    assert fdp_client.get_headers() == {"Authorization": "Bearer 1234abcd", "Content-Type": "text/turtle"}


def test_fdp_login_error(requests_mock):
    requests_mock.post("http://fdp.example.com/tokens", status_code=403)

    with pytest.raises(requests.HTTPError):
        FDPClient("http://fdp.example.com", "wrong_email", "wrong_password")


def test_fdp_publish(requests_mock, fdp_client_mock):
    requests_mock.put(
        "https://fdp.example.com/dataset/12345678/meta/state",
    )

    fdp_client_mock.publish_record("https://fdp.example.com/dataset/12345678")

    assert requests_mock.call_count == 2
    assert requests_mock.last_request.url == "https://fdp.example.com/dataset/12345678/meta/state"
    assert requests_mock.last_request.json() == {"current": "PUBLISHED"}


@pytest.mark.parametrize("metadata_type", ["dataset", "catalog", "distribution"])
def test_fdp_post_serialised(requests_mock, fdp_client_mock, metadata_type):
    requests_mock.post(f"http://fdp.example.com/{metadata_type}", text="")

    metadata = MagicMock(spec=Graph)
    metadata.serialize.return_value = ""
    # Ensure it's valid? Enforce lowercase?
    fdp_client_mock.post_serialized(metadata_type, metadata)

    assert requests_mock.last_request.url == f"http://fdp.example.com/{metadata_type}"
    assert requests_mock.last_request.headers["Content-Type"] == "text/turtle"
    assert requests_mock.last_request.headers["Authorization"] == "Bearer 1234abcd"
    metadata.serialize.assert_called_once_with(format="turtle")


# @pytest.mark.repeat(1)
@patch("img2catalog.fdpclient.FDPClient.post_serialized")
@patch("img2catalog.fdpclient.FDPClient.publish_record")
def test_fdp_create_and_publish(publish_record, post_serialized, requests_mock, fdp_client_mock):
    requests_mock.post("http://fdp.example.com/dataset", text="")
    empty_graph = Graph()

    # load the reference file and return it as post_response text with code 201 ('Created')
    # The FDP reference implementation returns the new identifier in HTTP location header
    fdp_response = requests.Response()
    fdp_response.status_code = 201
    fdp_response.headers = {"Location": "http://fdp.example.com/dataset/f1bcfd31-397e-4955-930c-663df8c2d9bf"}
    # requests expects a binary response content, not a string
    with open(file="tests/references/fdp_dataset.ttl", mode="rb") as f:
        fdp_response._content = f.read()

    post_serialized.return_value = fdp_response

    fdp_client_mock.create_and_publish("dataset", empty_graph)

    publish_record.assert_called_once_with(
        URIRef("http://fdp.example.com/dataset/f1bcfd31-397e-4955-930c-663df8c2d9bf")
    )
    post_serialized.assert_called_once_with(resource_type="dataset", metadata=empty_graph)
