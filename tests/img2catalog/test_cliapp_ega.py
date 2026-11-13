import logging
import pathlib
from unittest.mock import patch

from rdflib import DCAT, RDF, Graph, URIRef

from img2catalog.cli_app import cli_click

EGA_EXAMPLE_CONFIG = pathlib.Path(__file__).parents[2] / "examples" / "ega" / "example_config.toml"


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_skips_dataset_with_empty_mandatory_value(
    fetch_ega_datasets, default_ega_dataset, isolated_cli_runner, caplog
):
    """A dataset without a description in EGA is skipped, while the other datasets are still mapped."""
    # Arrange
    untitled_dataset = {**default_ega_dataset, "accession_id": "EGAD00010000500", "description": None}
    fetch_ega_datasets.return_value = [default_ega_dataset, untitled_dataset]

    # Act
    with caplog.at_level(logging.WARNING):
        result = isolated_cli_runner.invoke(
            cli_click,
            [
                "-c",
                str(EGA_EXAMPLE_CONFIG),
                "ega",
                "-a",
                "EGAD00001005083",
                "-a",
                "EGAD00010000500",
                "map-ega-hriv2",
                "rdf",
                "-o",
                "output.ttl",
            ],
        )

    # Assert
    assert result.exit_code == 0, result.output
    graph = Graph().parse("output.ttl")
    assert set(graph.subjects(RDF.type, DCAT.Dataset)) == {
        URIRef("http://img2catalog.internal/dataset/EGAD00001005083")
    }
    # The Distribution of the skipped dataset is left out too
    assert set(graph.subjects(RDF.type, DCAT.Distribution)) == {
        URIRef("http://img2catalog.internal/distribution/EGAD00001005083/BIN")
    }
    assert set(graph.objects(URIRef("http://img2catalog.internal/catalog/ega"), DCAT.dataset)) == {
        URIRef("http://img2catalog.internal/dataset/EGAD00001005083")
    }
    assert "Skipping EGA dataset EGAD00010000500: EGA dataset EGAD00010000500 has no description" in caplog.text
