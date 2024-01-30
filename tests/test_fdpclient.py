import pytest
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


# post_serialized: check if stuff gets posted
# check if correct content type is used
