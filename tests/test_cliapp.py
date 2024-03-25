import pathlib
import sys
from unittest.mock import ANY, MagicMock, Mock, patch

import pytest
from rdflib import DCAT, DCTERMS, Graph

from img2catalog.cli_app import cli_click, load_img2catalog_configuration
from img2catalog.const import VCARD, XNAT_HOST_ENV, XNAT_PASS_ENV, XNAT_USER_ENV, XNATPY_HOST_ENV

TEST_CONFIG = pathlib.Path(__file__).parent / "example-config.toml"


@pytest.fixture()
def empty_graph():
    graph = Graph()
    graph.bind("dcat", DCAT)
    graph.bind("dcterms", DCTERMS)
    graph.bind("v", VCARD)
    return graph


@pytest.fixture()
def toml_patch_target():
    # Python 3.11 and up has tomllib built-in, for 3.10 and lower we use tomli which provides
    # the same functonality. We check if it's Python 3.10 or lower to patch the correct target.
    if sys.version_info[0] == 3 and sys.version_info[1] <= 10:
        return "tomli.load"
    else:
        return "tomllib.load"


@patch("xnat.connect")
@patch("img2catalog.cli_app.xnat_to_RDF")
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
@patch("img2catalog.cli_app.xnat_to_RDF")
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
@patch("img2catalog.cli_app.xnat_to_RDF")
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
@patch("img2catalog.cli_app.xnat_to_RDF")
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
@patch("img2catalog.cli_app.xnat_to_RDF")
def test_user_pass_prio_env(xnat_to_RDF, connect, empty_graph, isolated_cli_runner, monkeypatch):
    # Mock context manager of xnatpy and the XNAT to RDF function
    connect.__enter__.return_value = True
    xnat_to_RDF.return_value = empty_graph

    monkeypatch.setenv(XNAT_USER_ENV, "fail_user")
    monkeypatch.setenv(XNAT_PASS_ENV, "fail_password")
    # monkeypatch.setenv(XNAT_HOST_ENV, "http://fail_test.example.com")
    # Run isolated (to keep log files safe)
    result = isolated_cli_runner.invoke(cli_click, ["-u", "pass_user", "-s", "http://test.example.com", "dcat"])

    # FIXME Not sure if this is desired behavior. Ideally, if the username is set as an argument,
    # it should prompt for the password or at least ignore the environment variable.
    connect.assert_called_once_with(server="http://test.example.com", user="pass_user", password=None)
    xnat_to_RDF.assert_called_once()

    assert result.exit_code == 0


@patch("xnat.connect")
@patch("img2catalog.cli_app.xnat_to_RDF")
def test_user_pass_envvar(xnat_to_RDF, connect, empty_graph, isolated_cli_runner, monkeypatch):
    # Mock context manager of xnatpy and the XNAT to RDF function
    connect.__enter__.return_value = True
    xnat_to_RDF.return_value = empty_graph

    monkeypatch.setenv(XNAT_USER_ENV, "pass_user")
    monkeypatch.setenv(XNAT_PASS_ENV, "password")
    # Run isolated (to keep log files safe)
    result = isolated_cli_runner.invoke(
        cli_click,
        ["-s", "http://test.example.com", "dcat"],
    )

    connect.assert_called_once_with(server="http://test.example.com", user="pass_user", password="password")
    xnat_to_RDF.assert_called_once()

    assert result.exit_code == 0


@patch("xnat.connect")
@patch("img2catalog.cli_app.xnat_to_RDF")
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
        load_img2catalog_configuration(config_path)


@pytest.mark.parametrize("config_param", [None, TEST_CONFIG])
@patch("img2catalog.configmanager.CONFIG_HOME_PATH", TEST_CONFIG)
@patch("builtins.open")
def test_config_dir(open, toml_patch_target, config_param):
    with patch(toml_patch_target) as load:
        load_img2catalog_configuration(config_param)
        # Make sure the correct configuration is loaded
        open.assert_called_once_with(TEST_CONFIG, "rb")
        # Make sure the file de-serializer is called, not the string de-serializer
        load.assert_called_once()


@pytest.mark.xfail(reason="Mocking FDP client seems to halt execution")
@patch("img2catalog.xnat_parser.xnat_to_FDP")
@patch("img2catalog.fdpclient.FDPClient")
@patch("xnat.connect")
def test_fdp_cli(connect, mock_FDPClient, xnat_to_FDP, isolated_cli_runner):
    connect.__enter__.return_value = True

    mock_FDPClient.return_value = None

    result = isolated_cli_runner.invoke(
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
        ],
    )
    # print(xnat_connect.call_count)
    # mock_FDPClient.assert_called()
    print(str(result.stdout_bytes.decode()))
    connect.assert_called_once_with(server="http://example.com", user=ANY, password=ANY)
    xnat_to_FDP.assert_called_once()
    pass


@patch("xnat.connect")
@patch("img2catalog.cli_app.xnat_to_DCATDataset")
def test_output_project(
    xnat_to_DCATDataset,
    connect,
    empty_graph,
    isolated_cli_runner,
):
    # patch the session.projects such that it returns the id it was called with
    connect.return_value.__enter__.return_value.projects.__getitem__.side_effect = lambda x: x

    # Always return an empty graph
    xnat_to_DCATDataset.return_value.to_graph.return_value = empty_graph

    with patch.object(empty_graph, "serialize") as serializer:
        result = isolated_cli_runner.invoke(
            cli_click,
            ["--verbose", "-s", "http://example.com", "project", "test_project"],
        )
        serializer.assert_called_once_with(format="turtle")

    connect.assert_called_once_with(server="http://example.com", user=ANY, password=ANY)
    xnat_to_DCATDataset.assert_called_with("test_project", ANY)

    connect.return_value.__enter__.return_value.projects.__getitem__.assert_called_once_with("test_project")


@patch("xnat.connect")
@patch("img2catalog.cli_app.xnat_to_DCATDataset")
def test_output_project_file(
    xnat_to_DCATDataset,
    connect,
    empty_graph,
    isolated_cli_runner,
):
    # patch the session.projects such that it returns the id it was called with
    connect.return_value.__enter__.return_value.projects.__getitem__.side_effect = lambda x: x

    # Always return an empty graph
    xnat_to_DCATDataset.return_value.to_graph.return_value = empty_graph

    with patch.object(empty_graph, "serialize") as serializer:
        result = isolated_cli_runner.invoke(
            cli_click,
            ["--verbose", "-s", "http://example.com", "project", "test_project", "-o", "test_project.xml", "-f", "xml"],
        )
        serializer.assert_called_once_with(format="xml", destination="test_project.xml")

    connect.assert_called_once_with(server="http://example.com", user=ANY, password=ANY)
    xnat_to_DCATDataset.assert_called_with("test_project", ANY)

    connect.return_value.__enter__.return_value.projects.__getitem__.assert_called_once_with("test_project")
