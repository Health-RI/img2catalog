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
    result = isolated_cli_runner.invoke(cli_click, ["--server", "http://example.com", "--verbose", "dcat"])

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
    result = isolated_cli_runner.invoke(cli_click, ["dcat"])

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
    result = isolated_cli_runner.invoke(cli_click, ["dcat"])

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
    result = isolated_cli_runner.invoke(cli_click, ["-u", "pass_user", "-s", "http://test.example.com", "dcat"])

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
        cli_click,
        ["-s", "http://test.example.com", "dcat"],
    )

    connect.assert_called_once_with(server="http://test.example.com", user="pass_user", password="password")

    assert result.exit_code == 0


@patch("xnat.connect")
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
    result = isolated_cli_runner.invoke(cli_click, ["-s", "http://example.com", "--config", "non_existing_file.toml"])

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
            "-s",
            "http://example.com",
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
        ["--verbose", "-s", "http://example.com", "project", "test_project"],
    )

    connect.assert_called_once_with(server="http://example.com", user=ANY, password=ANY)
    mock_project_to_dataset.assert_called_once_with('test_project')


# @patch("xnat.connect")
# @patch("img2catalog.cli_app.xnat_to_DCATDataset")
# def test_output_project(
#     xnat_to_DCATDataset,
#     connect,
#     mock_dataset,
#     empty_graph,
#     isolated_cli_runner,
# ):
#     """ Test CLI for one project, stdout
#
#     This CLI should only retrieve metadata of the project `test_project` and only return that dataset.
#     The output is parsed from stdout.
#     """
#     # patch the session.projects such that it returns the id it was called with
#     connect.return_value.__enter__.return_value.projects.__getitem__.side_effect = lambda x: x
#
#     # Always return a mock DCATDataset object and URI
#     xnat_to_DCATDataset.return_value = (mock_dataset, URIRef("http://example.com"))
#
#     result = isolated_cli_runner.invoke(
#         cli_click,
#         ["--verbose", "-s", "http://example.com", "project", "test_project"],
#     )
#
#     result_graph = empty_graph.parse(result.stdout_bytes, format="ttl")
#     reference_graph = empty_graph.parse(source=pathlib.Path(__file__).parent / "references" / "mock_dataset.ttl")
#
#     # Verify known output
#     assert to_isomorphic(reference_graph) == to_isomorphic(result_graph)
#
#     connect.assert_called_once_with(server="http://example.com", user=ANY, password=ANY)
#     xnat_to_DCATDataset.assert_called_with("test_project", ANY)
#     connect.return_value.__enter__.return_value.projects.__getitem__.assert_called_once_with("test_project")


# @patch("xnat.connect")
# @patch("img2catalog.cli_app.xnat_to_DCATDataset")
# def test_output_project_file(
#     xnat_to_DCATDataset,
#     connect,
#     mock_dataset,
#     empty_graph,
#     isolated_cli_runner,
# ):
#     """ Test CLI for one project, output file
#
#     This CLI should only retrieve metadata of the project `test_project` and only return that dataset.
#     The output is parsed from an output file.
#     """
#     # patch the session.projects such that it returns the id it was called with
#     connect.return_value.__enter__.return_value.projects.__getitem__.side_effect = lambda x: x
#
#     # Always return a mock DCATDataset object and URI
#     xnat_to_DCATDataset.return_value = (mock_dataset, URIRef("http://example.com"))
#
#     isolated_cli_runner.invoke(
#         cli_click,
#         ["--verbose", "-s", "http://example.com", "project", "test_project", "-o", "test_project.xml", "-f", "xml"],
#     )
#
#     result_graph = empty_graph.parse(source="test_project.xml", format="xml")
#     reference_graph = empty_graph.parse(source=pathlib.Path(__file__).parent / "references" / "mock_dataset.ttl")
#
#     # Verify known output
#     assert to_isomorphic(reference_graph) == to_isomorphic(result_graph)
#
#     # Make sure right functions are called
#     connect.assert_called_once_with(server="http://example.com", user=ANY, password=ANY)
#     xnat_to_DCATDataset.assert_called_with("test_project", ANY)
#     connect.return_value.__enter__.return_value.projects.__getitem__.assert_called_once_with("test_project")
