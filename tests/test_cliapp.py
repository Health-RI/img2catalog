import pathlib
from unittest.mock import ANY, Mock, patch, MagicMock

import pytest
from rdflib import URIRef
from rdflib.compare import to_isomorphic

from img2catalog.cli_app import cli_click, load_img2catalog_configuration
from img2catalog.const import (
    XNAT_HOST_ENV,
    XNAT_PASS_ENV,
    XNAT_USER_ENV,
    XNATPY_HOST_ENV,
    SPARQL_ENV,
    FDP_USER_ENV,
    FDP_PASS_ENV,
    FDP_SERVER_ENV,
)
from img2catalog.inputs.xnat import XNATInput
from img2catalog.outputs.rdf import RDFOutput

TEST_CONFIG = pathlib.Path(__file__).parent / "example-config.toml"


@patch("xnat.connect")
def test_cli_connect(connect, isolated_cli_runner):
    """ Test CLI connect

    Test if calling `img2catalog dcat` works.
    """

    # Mock context manager of xnatpy
    mock_xnat_session = MagicMock()
    mock_xnat_session.url_for.return_value = "http://example.com"

    connect.return_value.__enter__.return_value = mock_xnat_session

    # Run isolated (to keep log files safe)
    result = isolated_cli_runner.invoke(cli_click, ["--verbose", "xnat", "--server", "http://example.com",
                                                    "map-xnat-hriv2", "rdf"])

    connect.assert_called_once_with(server="http://example.com", user=None, password=None)
    assert result.exit_code == 0


@patch("xnat.connect")
def test_anonymous_envhost(connect, isolated_cli_runner, monkeypatch):
    """ Test XNATPY_HOST_ENV

    Test that `img2catalog dcat` uses the XNAT server configuration set through
    `XNATPY_HOST_ENV` and not `XNAT_HOST_ENV`, when both are set.
    """
    # Mock context manager of xnatpy
    mock_xnat_session = MagicMock()
    mock_xnat_session.url_for.return_value = "http://test.example.com"

    connect.return_value.__enter__.return_value = mock_xnat_session

    monkeypatch.setenv(XNATPY_HOST_ENV, "http://test.example.com")
    monkeypatch.setenv(XNAT_HOST_ENV, "http://fail_test.example.com")

    # Run isolated (to keep log files safe)
    result = isolated_cli_runner.invoke(cli_click, ["xnat", "map-xnat-hriv2", "rdf"])

    connect.assert_called_once_with(server="http://test.example.com", user=None, password=None)

    assert result.exit_code == 0


@patch("xnat.connect")
def test_second_env_var(connect, isolated_cli_runner, monkeypatch):
    """ Test XNAT_HOST_ENV

    Test that `img2catalog dcat` uses the XNAT server configuration set through
    `XNAT_HOST_ENV`, when it is set and `XNATPY_HOST_ENV` is not.
    """
    # Mock context manager of xnatpy
    mock_xnat_session = MagicMock()
    mock_xnat_session.url_for.return_value = "http://pass_test.example.com"

    connect.return_value.__enter__.return_value = mock_xnat_session

    # monkeypatch.setenv(XNATPY_HOST_ENV, "http://test.example.com")
    monkeypatch.setenv(XNAT_HOST_ENV, "http://pass_test.example.com")
    # Run isolated (to keep log files safe)
    result = isolated_cli_runner.invoke(cli_click, ["xnat", "map-xnat-hriv2", "rdf"])

    connect.assert_called_once_with(server="http://pass_test.example.com", user=None, password=None)

    assert result.exit_code == 0


# @pytest.mark.xfail(reason="Clearing password not implemented yet")
@patch("xnat.connect")
def test_user_pass_prio_env(connect, isolated_cli_runner, monkeypatch):
    """ Test credentials CLI priority

    Test that `img2catalog dcat` uses the credentials set through the CLI, and not through `XNAT_USER_ENV` and
    `XNAT_PASS_ENV`. When only one of the two is set through the CLI, both environment variables should still be
    ignored.
    """
    # Mock context manager of xnatpy and the XNAT to RDF function
    mock_xnat_session = MagicMock()
    mock_xnat_session.url_for.return_value = "http://test.example.com"

    connect.return_value.__enter__.return_value = mock_xnat_session

    monkeypatch.setenv(XNAT_USER_ENV, "fail_user")
    monkeypatch.setenv(XNAT_PASS_ENV, "fail_password")
    # monkeypatch.setenv(XNAT_HOST_ENV, "http://fail_test.example.com")
    # Run isolated (to keep log files safe)
    result = isolated_cli_runner.invoke(cli_click, ["xnat", "-u", "pass_user", "-s", "http://test.example.com",
                                                    "map-xnat-hriv2", "rdf"])

    # FIXME Not sure if this is desired behavior. Ideally, if the username is set as an argument,
    # it should prompt for the password or at least ignore the environment variable.
    connect.assert_called_once_with(server="http://test.example.com", user="pass_user", password=None)

    assert result.exit_code == 0


@patch("xnat.connect")
def test_user_pass_envvar(connect, isolated_cli_runner, monkeypatch):
    """ Test credentials environment variables.

    Test that `img2catalog dcat` uses the credentials set through `XNAT_USER_ENV` and `XNAT_PASS_ENV`,
    when none are supplied through the CLI.
    """
    # Mock context manager of xnatpy and the XNAT to RDF function
    mock_xnat_session = MagicMock()
    mock_xnat_session.url_for.return_value = "http://test.example.com"

    connect.return_value.__enter__.return_value = mock_xnat_session

    monkeypatch.setenv(XNAT_USER_ENV, "pass_user")
    monkeypatch.setenv(XNAT_PASS_ENV, "password")
    # Run isolated (to keep log files safe)
    result = isolated_cli_runner.invoke(
        cli_click, ["xnat", "-s", "http://test.example.com", "map-xnat-hriv2", "rdf"],
    )

    connect.assert_called_once_with(server="http://test.example.com", user="pass_user", password="password")

    assert result.exit_code == 0


@patch("xnat.connect")
@pytest.mark.parametrize(
    "test_input, expected",
    [
        (["xnat", "-s", "http://test.example.com", "map-xnat-hriv2", "rdf"], {"format": "turtle"}),
        (
            [
                "xnat", "-s", "http://test.example.com",
                "map-xnat-hriv2",
                "rdf", "-o", "tester_1.ttl", "-f", "xml",
            ],
            {"destination": "tester_1.ttl", "format": "xml"},
        ),
        (
            [
                "xnat", "-s", "http://test.example.com",
                "map-xnat-hriv2",
                "rdf", "-o", "tester_2.ttl",
            ],
            {"destination": "tester_2.ttl", "format": "turtle"},
        ),
    ],
)
def test_serialize_cli_args(connect, test_input, expected, empty_graph, isolated_cli_runner):
    """ Test CLI input for RDF serialization

    See the parametrize decorator for the CLI input and the expected output.
    """
    def mock_init(self, config, format='turtle'):
        self.config = config
        self.format = format

    # Mock context manager of xnatpy and the XNAT to RDF function
    mock_xnat_session = MagicMock()
    mock_xnat_session.url_for.return_value = "http://test.example.com"

    connect.return_value.__enter__.return_value = mock_xnat_session

    # Run isolated (to keep log files clean)
    with patch.object(RDFOutput, "__init__", autospec=True, return_value=None) as initializer:
        initializer.side_effect = mock_init
        result = isolated_cli_runner.invoke(
            cli_click,
            test_input,
        )
        initializer.assert_called_once()

    connect.assert_called_once_with(server="http://test.example.com", user=None, password=None)

    assert result.exit_code == 0



@patch("xnat.connect")
def test_nonexisting_config(connect, isolated_cli_runner):
    """ Test nonexisting configuration

    The CLI should return exit code 2 and not proceed to connecting to XNAT if a nonexisting configuration
    file is supplied.
    """
    result = isolated_cli_runner.invoke(cli_click, ["--config", "non_existing_file.toml",
                                                    "xnat", "-s", "http://example.com"])

    assert not connect.called, "Function was called despite having to error out"

    # Click says that a UsageError should have exit code 2.
    assert result.exit_code == 2


def test_config_loader_error():
    """ Test config loader error

    The function load_img2catalog_configuration() should return a FileNotFoundError if the config file does not exist.
    """
    config_path = Mock(spec=pathlib.Path)
    config_path.exists.return_value = False

    with pytest.raises(FileNotFoundError):
        load_img2catalog_configuration(config_path)


@pytest.mark.parametrize("config_param", [None, TEST_CONFIG])
@patch("img2catalog.configmanager.CONFIG_HOME_PATH", TEST_CONFIG)
@patch("builtins.open")
def test_config_dir(fileopen, toml_patch_target, config_param):
    """ Test config dir

    If config_param is `None`, no files should be opened; an example config is loaded from a hardcoded string.
    If config_param is `TEST_CONFIG`, this file should be loaded.
    In both cases the right toml loader should be called.
    """
    with patch(toml_patch_target) as load:
        load_img2catalog_configuration(config_param)
        # Make sure the correct configuration is loaded
        fileopen.assert_called_once_with(TEST_CONFIG, "rb")
        # Make sure the file de-serializer is called, not the string de-serializer
        load.assert_called_once()


@patch("img2catalog.outputs.fdp.FDPOutput.__init__")
@patch("fairclient.fdpclient.FDPClient.__init__")
@patch("xnat.connect")
def test_fdp_cli(connect, mock_FDPClient, mock_FDPOutput, isolated_cli_runner):
    """ Test CLI push to FDP, using CLI configuration """
    connect.__enter__.return_value = True

    mock_FDPClient.return_value = None

    isolated_cli_runner.invoke(
        cli_click,
        [
            "--verbose",
            "xnat",
            "-s",
            "http://example.com",
            "map-xnat-hriv2",
            "fdp",
            "--fdp",
            "http://fdp.example.com",
            "-u",
            "test",
            "-p",
            "more_test",
            "-c",
            "http://catalog.example.com",
        ],
    )

    connect.assert_called_once_with(server="http://example.com", user=ANY, password=ANY)
    mock_FDPOutput.assert_called_once()


@patch("fairclient.fdpclient.FDPClient.__init__")
@patch("fairclient.sparqlclient.FDPSPARQLClient.__init__")
@patch("xnat.connect")
def test_fdp_cli_env(connect, mock_SPARQLClient, mock_FDPClient, isolated_cli_runner, monkeypatch):
    """ Test CLI push to FDP, using environment variables configuration """
    connect.__enter__.return_value = True

    mock_FDPClient.return_value = None
    mock_SPARQLClient.return_value = None

    monkeypatch.setenv(XNAT_HOST_ENV, "http://example.com")
    monkeypatch.setenv(FDP_USER_ENV, "userFDP")
    monkeypatch.setenv(FDP_PASS_ENV, "passwordFDP")
    monkeypatch.setenv(FDP_SERVER_ENV, "http://fdp.example.com")
    monkeypatch.setenv(SPARQL_ENV, "http://sparql.example.com")

    isolated_cli_runner.invoke(
        cli_click,
        [
            "--verbose",
            "xnat",
            "map-xnat-hriv2",
            "fdp",
            "-c",
            "http://catalog.example.com",
        ],
    )

    mock_FDPClient.assert_called_once_with("http://fdp.example.com", "userFDP", "passwordFDP")
    mock_SPARQLClient.assert_called_once_with(URIRef("http://sparql.example.com"))
    connect.assert_called_once_with(server="http://example.com", user=ANY, password=ANY)


@patch("xnat.connect")
@patch.object(XNATInput, 'project_to_dataset')
def test_output_project(
        mock_project_to_dataset,
        connect,
        mock_dataset,
        empty_graph,
        isolated_cli_runner,
):
    """ Test CLI for one project, stdout

    This CLI should only retrieve metadata of the project `test_project` and only return that dataset.
    The output is parsed from stdout.
    """
    connect.return_value.__enter__.return_value.projects.__getitem__.side_effect = lambda x: x

    result = isolated_cli_runner.invoke(
        cli_click,
        ["--verbose", "xnat-project", "-s", "http://example.com", "test_project",
         "map-xnat-hriv2", "rdf"],
    )

    connect.assert_called_once_with(server="http://example.com", user=ANY, password=ANY)
    mock_project_to_dataset.assert_called_once_with('test_project')
