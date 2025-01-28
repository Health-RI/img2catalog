import pathlib

from rdflib.compare import to_isomorphic

from img2catalog.cli_app import cli_click
from freezegun import freeze_time

# XNAT integration tests
# 5 projects; 1 public with optout keyword, 1 public without any keywords, 1 public with optin keyword,
# 1 protected with optin keyword, 1 private with optin keyword

TEST_CONFIG = pathlib.Path(__file__).parent / "xnat_integration_test_config.toml"

@freeze_time("2024-04-01")
def test_xnat_integration(tmp_path, xnat4tests_connection, xnat4tests_uri, isolated_cli_runner, empty_graph):
    result = isolated_cli_runner.invoke(cli_click, ["--server", xnat4tests_uri, "--verbose",
                                                    "--config", f"{TEST_CONFIG}", "dcat",
                                                    "-o", f"{tmp_path}/output.ttl"])
    result_graph = empty_graph.parse(source=f"{tmp_path}/output.ttl")
    reference_graph = empty_graph.parse(source=pathlib.Path(__file__).parent / "references" / "xnat_integration_test.ttl")

    # Verify known output
    assert result.exit_code == 0
    assert to_isomorphic(reference_graph) == to_isomorphic(result_graph)
