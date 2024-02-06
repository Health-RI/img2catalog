import pathlib
from unittest.mock import Mock, patch

import pytest
from rdflib import DCAT, DCTERMS, Graph

from xnatdcat.cli_app import cli_click, load_xnatdcat_configuration
from xnatdcat.const import VCARD, XNAT_HOST_ENV, XNAT_PASS_ENV, XNAT_USER_ENV, XNATPY_HOST_ENV


@pytest.fixture()
def empty_graph():
    graph = Graph()
    graph.bind("dcat", DCAT)
    graph.bind("dcterms", DCTERMS)
    graph.bind("v", VCARD)
    return graph


@patch("xnat.connect")
@patch("xnatdcat.cli_app.xnat_to_RDF")
def test_cli_connect(xnat_to_RDF, connect, empty_graph, isolated_cli_runner):
    # Mock context manager of xnatpy and the XNAT to RDF function
    connect.__enter__.return_value = True
    xnat_to_RDF.return_value = empty_graph

    # Run isolated (to keep log files safe)
    result = isolated_cli_runner.invoke(cli_click, ["--server", "http://example.com", "--verbose", "dcat"])

    print(result.output)

    connect.assert_called_once_with(server="http://example.com", user=None, password=None)
    xnat_to_RDF.assert_called_once()

    assert result.exit_code == 0


@patch("xnat.connect")
@patch("xnatdcat.cli_app.xnat_to_RDF")
def test_example_cli(xnat_to_RDF, connect, empty_graph, isolated_cli_runner):
    # Mock context manager of xnatpy and the XNAT to RDF function
    connect.__enter__.return_value = True
    xnat_to_RDF.return_value = empty_graph

    # Run isolated (to keep log files safe)
    result = isolated_cli_runner.invoke(cli_click, ["--verbose", "-s", "http://example.com", "dcat"])

    connect.assert_called_once_with(server="http://example.com", user=None, password=None)
    xnat_to_RDF.assert_called_once()

    assert result.exit_code == 0

    # assert False


@patch("xnat.connect")
@patch("xnatdcat.cli_app.xnat_to_RDF")
def test_anonymous_envhost(xnat_to_RDF, connect, empty_graph, isolated_cli_runner, monkeypatch):
    # Mock context manager of xnatpy and the XNAT to RDF function
    connect.__enter__.return_value = True
    xnat_to_RDF.return_value = empty_graph

    monkeypatch.setenv(XNATPY_HOST_ENV, "http://test.example.com")
    monkeypatch.setenv(XNAT_HOST_ENV, "http://fail_test.example.com")

    # Run isolated (to keep log files safe)
    result = isolated_cli_runner.invoke(cli_click, ["dcat"])

    connect.assert_called_once_with(server="http://test.example.com", user=None, password=None)
    xnat_to_RDF.assert_called_once()

    assert result.exit_code == 0


@patch("xnat.connect")
@patch("xnatdcat.cli_app.xnat_to_RDF")
def test_second_env_var(xnat_to_RDF, connect, empty_graph, isolated_cli_runner, monkeypatch):
    # Mock context manager of xnatpy and the XNAT to RDF function
    connect.__enter__.return_value = True
    xnat_to_RDF.return_value = empty_graph

    # monkeypatch.setenv(XNATPY_HOST_ENV, "http://test.example.com")
    monkeypatch.setenv(XNAT_HOST_ENV, "http://pass_test.example.com")
    # Run isolated (to keep log files safe)
    result = isolated_cli_runner.invoke(cli_click, ["dcat"])

    connect.assert_called_once_with(server="http://pass_test.example.com", user=None, password=None)
    xnat_to_RDF.assert_called_once()

    assert result.exit_code == 0


# @pytest.mark.xfail(reason="Clearing password not implemented yet")
@patch("xnat.connect")
@patch("xnatdcat.cli_app.xnat_to_RDF")
def test_user_pass_prio_env(xnat_to_RDF, connect, empty_graph, isolated_cli_runner, monkeypatch):
    # Mock context manager of xnatpy and the XNAT to RDF function
    connect.__enter__.return_value = True
    xnat_to_RDF.return_value = empty_graph

    monkeypatch.setenv(XNAT_USER_ENV, "fail_user")
    monkeypatch.setenv(XNAT_PASS_ENV, "fail_password")
    # monkeypatch.setenv(XNAT_HOST_ENV, "http://fail_test.example.com")
    # Run isolated (to keep log files safe)
    result = isolated_cli_runner.invoke(cli_click, ["-u", "pass_user", '-s', "http://test.example.com", "dcat"])

    # FIXME Not sure if this is desired behavior. Ideally, if the username is set as an argument,
    # it should prompt for the password or at least ignore the environment variable.
    connect.assert_called_once_with(server="http://test.example.com", user="pass_user", password=None)
    xnat_to_RDF.assert_called_once()

    assert result.exit_code == 0


@patch("xnat.connect")
@patch("xnatdcat.cli_app.xnat_to_RDF")
def test_user_pass_envvar(xnat_to_RDF, connect, empty_graph, isolated_cli_runner, monkeypatch):
    # Mock context manager of xnatpy and the XNAT to RDF function
    connect.__enter__.return_value = True
    xnat_to_RDF.return_value = empty_graph

    monkeypatch.setenv(XNAT_USER_ENV, "pass_user")
    monkeypatch.setenv(XNAT_PASS_ENV, "password")
    # Run isolated (to keep log files safe)
    result = isolated_cli_runner.invoke(
        cli_click,
        ['-s', "http://test.example.com", "dcat"],
    )

    connect.assert_called_once_with(server="http://test.example.com", user="pass_user", password="password")
    xnat_to_RDF.assert_called_once()

    assert result.exit_code == 0


@patch("xnat.connect")
@patch("xnatdcat.cli_app.xnat_to_RDF")
@pytest.mark.parametrize(
    "test_input, expected",
    [
        (["-s", "http://test.example.com", "dcat"], {"format": "turtle"}),
        (
            [
                "-s",
                "http://test.example.com",
                "dcat",
                "-o",
                "tester_1.ttl",
                "-f",
                "xml",
            ],
            {"destination": "tester_1.ttl", "format": "xml"},
        ),
        (
            [
                "-s",
                "http://test.example.com",
                "dcat",
                "-o",
                "tester_2.ttl",
            ],
            {"destination": "tester_2.ttl", "format": "turtle"},
        ),
    ],
)
def test_serialize_cli_args(xnat_to_RDF, connect, test_input, expected, empty_graph, isolated_cli_runner):
    # Mock context manager of xnatpy and the XNAT to RDF function
    connect.__enter__.return_value = True
    xnat_to_RDF.return_value = empty_graph

    # Run isolated (to keep log files clean)
    with patch.object(empty_graph, "serialize") as serializer:
        result = isolated_cli_runner.invoke(
            cli_click,
            test_input,
        )
        serializer.assert_called_once_with(**expected)

    connect.assert_called_once_with(server="http://test.example.com", user=None, password=None)
    xnat_to_RDF.assert_called_once()

    assert result.exit_code == 0


@patch("xnat.connect")
def test_nonexisting_config(connect, isolated_cli_runner):
    result = isolated_cli_runner.invoke(cli_click, ["-s", "http://example.com", "--config", "non_existing_file.toml"])

    assert not connect.called, "Function was called despite having to error out"

    # Click says that a UsageError should have exit code 2.
    assert result.exit_code == 2


def test_config_loader_error():
    config_path = Mock(spec=pathlib.Path)
    config_path.exists.return_value = False

    with pytest.raises(FileNotFoundError):
        load_xnatdcat_configuration(config_path)
