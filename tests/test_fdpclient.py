from unittest.mock import MagicMock, Mock, patch
import pytest
from rdflib import Graph, URIRef
import requests

from xnatdcat.fdpclient import FDPClient


# login:
# Check if token gets correctly assigned
# Check an exception gets raised for wrong credentials
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


def test_fdp_publish(requests_mock):
    requests_mock.post("http://fdp.example.com/tokens", json={"token": "1234abcd"})

    fdp_client = FDPClient("http://fdp.example.com", "user@example.com", "pass")

    requests_mock.put(
        "https://fdp.example.com/dataset/12345678/meta/state",
    )

    fdp_client.publish_record("https://fdp.example.com/dataset/12345678")

    assert requests_mock.call_count == 2
    assert requests_mock.last_request.url == "https://fdp.example.com/dataset/12345678/meta/state"
    assert requests_mock.last_request.json() == {"current": "PUBLISHED"}


def test_fdp_post_serialised(requests_mock):
    requests_mock.post("http://fdp.example.com/tokens", json={"token": "1234abcd"})
    requests_mock.post("http://fdp.example.com/dataset", text='')
    fdp_client = FDPClient("http://fdp.example.com", "user@example.com", "pass")

    metadata = MagicMock(spec=Graph)
    metadata.serialize.return_value = ''
    # Ensure it's valid? Enforce lowercase?
    fdp_client.post_serialized("dataset", metadata)

    assert requests_mock.last_request.url == "http://fdp.example.com/dataset"
    assert requests_mock.last_request.headers['Content-Type'] == 'text/turtle'
    assert requests_mock.last_request.headers['Authorization'] == 'Bearer 1234abcd'
    metadata.serialize.assert_called_once_with(format="turtle")
    # pass


# @pytest.mark.repeat(1)
@patch("xnatdcat.fdpclient.FDPClient.post_serialized")
@patch("xnatdcat.fdpclient.FDPClient.publish_record")
def test_fdp_create_and_publish(publish_record, post_serialized, requests_mock):
    requests_mock.post("http://fdp.example.com/tokens", json={"token": "1234abcd"})
    requests_mock.post("http://fdp.example.com/dataset", text='')
    fdp_client = FDPClient("http://fdp.example.com", "user@example.com", "pass")
    empty_graph = Graph()

    # load the reference file and return it as post_response text with code 201 ('Created')
    resp = requests.Response()
    resp.status_code = 201
    resp.headers = {'Location': "http://fdp.example.com/dataset/f1bcfd31-397e-4955-930c-663df8c2d9bf"}
    with open(file='tests/references/fdp_dataset.ttl', mode='rb') as f:
        resp._content = f.read()

    # publish_record.side_effect = FDPClient.create_and_publish
    post_serialized.return_value = resp

    fdp_client.create_and_publish('dataset', empty_graph)

    publish_record.assert_called_once_with(
        URIRef("http://fdp.example.com/dataset/f1bcfd31-397e-4955-930c-663df8c2d9bf")
    )
    post_serialized.assert_called_once_with(resource_type="dataset", metadata=empty_graph)
