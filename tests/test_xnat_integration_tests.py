import pathlib
import pytest

from rdflib.compare import to_isomorphic

from img2catalog.cli_app import cli_click
from freezegun import freeze_time


TEST_CONFIG = pathlib.Path(__file__).parent / "xnat_integration_test_config.toml"

@freeze_time("2024-04-01")
@pytest.mark.integration
def test_xnat_integration(tmp_path, xnat4tests_connection, xnat4tests_uri, isolated_cli_runner,
                          empty_graph, second_empty_graph):
    """ XNAT Integration test

    Using xnat4tests, there is a local XNAT prepared with 5 projects:
    - 1 public with the opt-out keyword,
    - 1 public without any keywords,
    - 1 private with optin keyword
    - 1 public with optin keyword,
    - 1 protected with optin keyword
    There is also some metadata inserted; see xnat4tests_fixture() in xnatpy_fixtures.py.

    Of these projects only the last two should be serialized.
    """
    # XNAT integration tests
    result = isolated_cli_runner.invoke(cli_click, ["--verbose", "--config", f"{TEST_CONFIG}",
                                                    "xnat", "--server", xnat4tests_uri, "-u", "admin", "-p", "admin",
                                                    "map-xnat-hriv2",
                                                    "rdf", "-o", f"{tmp_path}/output.ttl"])
    print(result.stdout)
    result_graph = empty_graph.parse(source=f"{tmp_path}/output.ttl")
    reference_graph = second_empty_graph.parse(
        source=pathlib.Path(__file__).parent / "references" / "xnat_integration_test.ttl")

    # Verify known output
    assert result.exit_code == 0
    assert to_isomorphic(reference_graph) == to_isomorphic(result_graph)


@freeze_time("2024-04-01")
@pytest.mark.integration
def test_xnat_integration_single_dataset(tmp_path, xnat4tests_connection, xnat4tests_uri, isolated_cli_runner,
                                         empty_graph, second_empty_graph):
    """ XNAT Integration test

    Using xnat4tests, there is a local XNAT prepared with 5 projects:
    - 1 public with the opt-out keyword,
    - 1 public without any keywords,
    - 1 private with optin keyword
    - 1 public with optin keyword,
    - 1 protected with optin keyword
    There is also some metadata inserted; see xnat4tests_fixture() in xnatpy_fixtures.py.

    In this test only 'protected_optin' will be serialized
    """
    # XNAT integration tests
    result = isolated_cli_runner.invoke(cli_click, ["--verbose", "--config", f"{TEST_CONFIG}",
                                                    "xnat-project", "--server", xnat4tests_uri, "-u", "admin", "-p", "admin",
                                                    "protected_optin",
                                                    "map-xnat-hriv2",
                                                    "rdf", "-o", f"{tmp_path}/output.ttl"])
    result_graph = empty_graph.parse(source=f"{tmp_path}/output.ttl")
    reference_graph = second_empty_graph.parse(source=pathlib.Path(__file__).parent / "references" / "xnat_integration_test-single_dataset.ttl")

    # Verify known output
    assert result.exit_code == 0
    assert to_isomorphic(reference_graph) == to_isomorphic(result_graph)
