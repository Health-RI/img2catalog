import copy
import logging
import pathlib
import re
from unittest.mock import patch

from rdflib import DCAT, RDF, Graph, URIRef

from img2catalog.cli_app import cli_click

EGA_EXAMPLE_CONFIG = pathlib.Path(__file__).parents[2] / "examples" / "ega" / "example_config.toml"

DATASET_URI = URIRef("http://img2catalog.internal/dataset/EGAD00001005083")
BIN_DISTRIBUTION_URI = URIRef("http://img2catalog.internal/distribution/EGAD00001005083/BIN")
TXT_DISTRIBUTION_URI = URIRef("http://img2catalog.internal/distribution/EGAD00001005083/TXT")
CATALOG_URI = URIRef("http://img2catalog.internal/catalog/ega")


def _config_without(tmp_path, *sections):
    """Write a copy of the EGA example config without the given tables (and their sub-tables)."""
    kept = []
    skipping = False
    for line in EGA_EXAMPLE_CONFIG.read_text().splitlines():
        header = re.match(r"\[([^\]]+)\]", line)
        if header:
            skipping = any(
                header.group(1) == section or header.group(1).startswith(f"{section}.") for section in sections
            )
        if not skipping:
            kept.append(line)
    config = tmp_path / "config.toml"
    config.write_text("\n".join(kept) + "\n")
    return config


def _run_map_ega_to_rdf(runner, config):
    return runner.invoke(
        cli_click,
        ["-c", str(config), "ega", "-a", "EGAD00001005083", "map-ega-hriv2", "rdf", "-o", "output.ttl"],
    )


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_fails_when_no_dataset_could_be_fetched(fetch_ega_datasets, isolated_cli_runner):
    """A run that fetched nothing must not look like a success."""
    # Arrange
    fetch_ega_datasets.return_value = []

    # Act
    result = _run_map_ega_to_rdf(isolated_cli_runner, EGA_EXAMPLE_CONFIG)

    # Assert
    assert result.exit_code != 0
    assert "None of the requested EGA datasets could be fetched" in result.output
    assert not pathlib.Path("output.ttl").exists()


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_links_dataset_distributions_and_catalog(fetch_ega_datasets, isolated_cli_runner, default_ega_dataset):
    """Files in two formats give a Distribution each, linked from the dataset, which the Catalog links in turn."""
    # Arrange
    default_ega_dataset["files"].append({"accession_id": "EGAF00000000003", "filesize": 500, "extension": "vcf"})
    fetch_ega_datasets.return_value = [default_ega_dataset]

    # Act
    result = _run_map_ega_to_rdf(isolated_cli_runner, EGA_EXAMPLE_CONFIG)

    # Assert
    assert result.exit_code == 0, result.output
    graph = Graph().parse("output.ttl")
    assert set(graph.objects(DATASET_URI, DCAT.distribution)) == {BIN_DISTRIBUTION_URI, TXT_DISTRIBUTION_URI}
    for distribution_uri in (BIN_DISTRIBUTION_URI, TXT_DISTRIBUTION_URI):
        assert (distribution_uri, RDF.type, DCAT.Distribution) in graph
    assert set(graph.subjects(RDF.type, DCAT.Catalog)) == {CATALOG_URI}
    assert set(graph.objects(CATALOG_URI, DCAT.dataset)) == {DATASET_URI}


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_leaves_catalog_out_without_catalog_config(
    fetch_ega_datasets, isolated_cli_runner, default_ega_dataset, tmp_path
):
    # Arrange
    fetch_ega_datasets.return_value = [default_ega_dataset]
    config = _config_without(tmp_path, "catalog")

    # Act
    result = _run_map_ega_to_rdf(isolated_cli_runner, config)

    # Assert
    assert result.exit_code == 0, result.output
    graph = Graph().parse("output.ttl")
    assert not list(graph.subjects(RDF.type, DCAT.Catalog))
    assert (DATASET_URI, RDF.type, DCAT.Dataset) in graph


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_fails_on_files_without_distribution_config(
    fetch_ega_datasets, isolated_cli_runner, default_ega_dataset, tmp_path
):
    """Files without a [distribution] section is a configuration error, reported as a usage error."""
    # Arrange
    fetch_ega_datasets.return_value = [default_ega_dataset]
    config = _config_without(tmp_path, "distribution")

    # Act
    result = _run_map_ega_to_rdf(isolated_cli_runner, config)

    # Assert
    assert result.exit_code == 2
    assert "EGAD00001005083 has files, but the configuration has no [distribution] section" in result.output
    assert not pathlib.Path("output.ttl").exists()


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_needs_no_distribution_config_without_files(
    fetch_ega_datasets, isolated_cli_runner, default_ega_dataset, tmp_path
):
    # Arrange
    dataset = copy.deepcopy(default_ega_dataset)
    dataset["files"] = []
    fetch_ega_datasets.return_value = [dataset]
    config = _config_without(tmp_path, "distribution")

    # Act
    result = _run_map_ega_to_rdf(isolated_cli_runner, config)

    # Assert
    assert result.exit_code == 0, result.output
    graph = Graph().parse("output.ttl")
    assert not list(graph.subjects(RDF.type, DCAT.Distribution))


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_skips_dataset_with_empty_mandatory_value(
    fetch_ega_datasets, default_ega_dataset, isolated_cli_runner, caplog
):
    """A dataset without a title in EGA is skipped, while the other datasets are still mapped."""
    # Arrange
    untitled_dataset = {**default_ega_dataset, "accession_id": "EGAD00010000500", "title": None}
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
    assert set(graph.subjects(RDF.type, DCAT.Dataset)) == {DATASET_URI}
    # The Distribution of the skipped dataset is left out too
    assert set(graph.subjects(RDF.type, DCAT.Distribution)) == {BIN_DISTRIBUTION_URI}
    assert set(graph.objects(CATALOG_URI, DCAT.dataset)) == {DATASET_URI}
    assert "Skipping EGA dataset EGAD00010000500: EGA dataset EGAD00010000500 has no title" in caplog.text
