import pytest
from unittest.mock import patch

from xnatdcat import cli_app
from xnatdcat.const import XNATPY_HOST_ENV, XNAT_HOST_ENV


def mock_xnatconnect(server, user, password, **kwargs):
    return server


@patch('argparse.ArgumentParser.parse_args')
def test_anonymous_envhost(args, mocker, monkeypatch):
    args.server = None
    args.username = None
    args.password = None

    monkeypatch.setenv(XNAT_HOST_ENV, "http://example.com")
    mocked_xnatconnect = mocker.patch('xnat.connect')
    mocked_xnatconnect.side_effect = mock_xnatconnect
    cli_app.__connect_xnat(args)
    mocked_xnatconnect.assert_called_once_with(server="http://example.com", user=None, password=None)


@patch('argparse.ArgumentParser.parse_args')
def test_anonymous_envhost2(args, mocker, monkeypatch):
    args.server = None
    args.username = None
    args.password = None

    monkeypatch.setenv(XNATPY_HOST_ENV, "http://test.example.com")
    mocked_xnatconnect = mocker.patch('xnat.connect')
    mocked_xnatconnect.side_effect = mock_xnatconnect
    cli_app.__connect_xnat(args)
    mocked_xnatconnect.assert_called_once_with(server="http://test.example.com", user=None, password=None)


@patch('argparse.ArgumentParser.parse_args')
def test_anonymous_prioritization(args, mocker, monkeypatch):
    args.server = None
    args.username = None
    args.password = None

    monkeypatch.setenv(XNAT_HOST_ENV, "http://example.com")
    monkeypatch.setenv(XNATPY_HOST_ENV, "http://test.example.com")
    mocked_xnatconnect = mocker.patch('xnat.connect')
    mocked_xnatconnect.side_effect = mock_xnatconnect
    cli_app.__connect_xnat(args)
    mocked_xnatconnect.assert_called_once_with(server="http://test.example.com", user=None, password=None)
