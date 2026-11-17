import logging
import pathlib
from unittest.mock import patch

from rdflib import DCAT, RDF, Graph

from img2catalog.cli_app import cli_click

EGA_EXAMPLE_CONFIG = pathlib.Path(__file__).parents[2] / "examples" / "ega" / "example_config.toml"


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_leaves_catalog_out_without_datasets(fetch_ega_datasets, isolated_cli_runner, caplog):
    """When no EGA dataset could be fetched, a Catalog without datasets is not made."""
    # Arrange
    fetch_ega_datasets.return_value = []

    # Act
    with caplog.at_level(logging.WARNING):
        result = isolated_cli_runner.invoke(
            cli_click,
            ["-c", str(EGA_EXAMPLE_CONFIG), "ega", "-a", "EGAD00001005083", "map-ega-hriv2", "rdf", "-o", "output.ttl"],
        )

    # Assert
    assert result.exit_code == 0, result.output
    graph = Graph().parse("output.ttl")
    assert not list(graph.subjects(RDF.type, DCAT.Catalog))
    assert "No EGA datasets were mapped, so the Catalog is left out" in caplog.text
