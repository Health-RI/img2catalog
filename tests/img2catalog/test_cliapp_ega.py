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


def _config_with(tmp_path, old, new):
    """Write a copy of the EGA example config in which the first occurrence of a line is replaced."""
    text = EGA_EXAMPLE_CONFIG.read_text()
    assert old in text
    config = tmp_path / "config.toml"
    config.write_text(text.replace(old, new, 1))
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
def test_ega_cli_gives_compressed_files_their_own_distribution(
    fetch_ega_datasets, isolated_cli_runner, default_ega_dataset
):
    """A .vcf and a .vcf.gz file have the same file type (TXT), so the compression must keep their URIs apart."""
    # Arrange
    default_ega_dataset["files"] = [
        {"accession_id": "EGAF00000000001", "filesize": 100, "extension": "vcf"},
        {"accession_id": "EGAF00000000002", "filesize": 200, "extension": "vcf.gz"},
    ]
    fetch_ega_datasets.return_value = [default_ega_dataset]
    gzip_distribution_uri = URIRef("http://img2catalog.internal/distribution/EGAD00001005083/TXT-gzip")

    # Act
    result = _run_map_ega_to_rdf(isolated_cli_runner, EGA_EXAMPLE_CONFIG)

    # Assert
    assert result.exit_code == 0, result.output
    graph = Graph().parse("output.ttl")
    assert set(graph.objects(DATASET_URI, DCAT.distribution)) == {TXT_DISTRIBUTION_URI, gzip_distribution_uri}
    assert (
        gzip_distribution_uri,
        DCAT.compressFormat,
        URIRef("http://www.iana.org/assignments/media-types/application/gzip"),
    ) in graph
    assert (TXT_DISTRIBUTION_URI, DCAT.compressFormat, None) not in graph


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
def test_ega_cli_fails_when_every_dataset_is_skipped(
    fetch_ega_datasets, default_ega_dataset, isolated_cli_runner, caplog
):
    """A run that maps nothing must not look like a success, as with a run that fetched nothing."""
    # Arrange
    fetch_ega_datasets.return_value = [{**default_ega_dataset, "description": None}]

    # Act
    with caplog.at_level(logging.WARNING):
        result = _run_map_ega_to_rdf(isolated_cli_runner, EGA_EXAMPLE_CONFIG)

    # Assert
    assert result.exit_code != 0
    assert "None of the EGA datasets could be mapped" in result.output
    assert "Skipping EGA dataset EGAD00001005083: EGA dataset EGAD00001005083 has no description" in caplog.text
    assert not pathlib.Path("output.ttl").exists()


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_skips_dataset_with_empty_mandatory_value(
    fetch_ega_datasets, default_ega_dataset, isolated_cli_runner, caplog
):
    """A dataset without a description in EGA is skipped, while the other datasets are still mapped."""
    # Arrange
    undescribed_dataset = {**default_ega_dataset, "accession_id": "EGAD00010000500", "description": None}
    fetch_ega_datasets.return_value = [default_ega_dataset, undescribed_dataset]

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
    # The other dataset is still written, but the run fails so that a scheduler notices the skipped dataset
    assert result.exit_code == 1, result.output
    assert "1 of the requested EGA datasets were skipped, see the warnings above: EGAD00010000500" in result.output
    graph = Graph().parse("output.ttl")
    assert set(graph.subjects(RDF.type, DCAT.Dataset)) == {DATASET_URI}
    # The Distribution of the skipped dataset is left out too
    assert set(graph.subjects(RDF.type, DCAT.Distribution)) == {BIN_DISTRIBUTION_URI}
    assert set(graph.objects(CATALOG_URI, DCAT.dataset)) == {DATASET_URI}
    assert "Skipping EGA dataset EGAD00010000500: EGA dataset EGAD00010000500 has no description" in caplog.text


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_fails_on_empty_mandatory_config_after_a_skipped_dataset(
    fetch_ega_datasets, default_ega_dataset, isolated_cli_runner, tmp_path
):
    """A skipped dataset must not hide a configuration error, which applies to every dataset."""
    # Arrange
    skipped_dataset = {**default_ega_dataset, "accession_id": "EGAD00010000500", "description": None}
    fetch_ega_datasets.return_value = [skipped_dataset, default_ega_dataset]
    config = _config_with(
        tmp_path,
        'theme = ["http://publications.europa.eu/resource/authority/data-theme/HEAL"]',
        'theme = [""]',
    )

    # Act
    result = _run_map_ega_to_rdf(isolated_cli_runner, config)

    # Assert
    assert result.exit_code == 2
    assert "Configuration value 'theme' is mandatory, but empty" in result.output
    assert not pathlib.Path("output.ttl").exists()


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_fails_on_empty_mandatory_catalog_config(
    fetch_ega_datasets, default_ega_dataset, isolated_cli_runner, tmp_path
):
    # Arrange
    fetch_ega_datasets.return_value = [default_ega_dataset]
    config = _config_with(tmp_path, 'title = "Example EGA catalog"', 'title = ""')

    # Act
    result = _run_map_ega_to_rdf(isolated_cli_runner, config)

    # Assert
    assert result.exit_code == 2
    assert "Configuration value 'title' is mandatory, but empty" in result.output
    assert not pathlib.Path("output.ttl").exists()


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_fails_on_missing_config_key(fetch_ega_datasets, default_ega_dataset, isolated_cli_runner, tmp_path):
    # Arrange
    fetch_ega_datasets.return_value = [default_ega_dataset]
    config = _config_with(tmp_path, 'access_rights = "', 'unused_access_rights = "')

    # Act
    result = _run_map_ega_to_rdf(isolated_cli_runner, config)

    # Assert
    assert result.exit_code == 2
    assert "The configuration has no 'access_rights'" in result.output


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_skips_dataset_with_unmappable_metadata(
    fetch_ega_datasets, default_ega_dataset, isolated_cli_runner, caplog
):
    """A list where EGA should have a text only skips that dataset, instead of aborting the run."""
    # Arrange
    listed_dataset = {**default_ega_dataset, "accession_id": "EGAD00010000500", "title": ["a", "b"]}
    fetch_ega_datasets.return_value = [listed_dataset, default_ega_dataset]

    # Act
    with caplog.at_level(logging.WARNING):
        result = _run_map_ega_to_rdf(isolated_cli_runner, EGA_EXAMPLE_CONFIG)

    # Assert
    assert result.exit_code == 1, result.output
    assert "skipped, see the warnings above: EGAD00010000500" in result.output
    graph = Graph().parse("output.ttl")
    assert set(graph.subjects(RDF.type, DCAT.Dataset)) == {DATASET_URI}
    assert "Skipping EGA dataset EGAD00010000500: Expected a single text value" in caplog.text


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_skips_dataset_the_model_refuses(fetch_ega_datasets, default_ega_dataset, isolated_cli_runner, caplog):
    """A value from EGA that the model refuses (a pydantic ValidationError) only skips that dataset."""
    # Arrange
    refused_dataset = {**default_ega_dataset, "accession_id": "EGAD00010000500", "num_samples": "many"}
    fetch_ega_datasets.return_value = [refused_dataset, default_ega_dataset]

    # Act
    with caplog.at_level(logging.WARNING):
        result = _run_map_ega_to_rdf(isolated_cli_runner, EGA_EXAMPLE_CONFIG)

    # Assert
    assert result.exit_code == 1, result.output
    assert "Skipping EGA dataset EGAD00010000500" in caplog.text
    assert set(Graph().parse("output.ttl").subjects(RDF.type, DCAT.Dataset)) == {DATASET_URI}


@patch("img2catalog.cli_app.map_ega_to_healthri_dcat_dataset")
@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_does_not_skip_datasets_on_a_bug_in_the_mapping(
    fetch_ega_datasets, map_ega_to_healthri_dcat_dataset, default_ega_dataset, isolated_cli_runner, caplog
):
    """A TypeError or ValueError from the mapping code itself is a bug, which must not look like bad EGA metadata."""
    # Arrange
    fetch_ega_datasets.return_value = [default_ega_dataset]
    map_ega_to_healthri_dcat_dataset.side_effect = TypeError("unsupported operand type(s)")

    # Act
    with caplog.at_level(logging.WARNING):
        result = _run_map_ega_to_rdf(isolated_cli_runner, EGA_EXAMPLE_CONFIG)

    # Assert
    assert result.exit_code == 1
    assert isinstance(result.exception, TypeError)
    assert "Skipping" not in caplog.text
    assert not pathlib.Path("output.ttl").exists()


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_fails_after_writing_when_a_dataset_could_not_be_fetched(
    fetch_ega_datasets, default_ega_dataset, isolated_cli_runner
):
    # Arrange
    fetch_ega_datasets.return_value = [default_ega_dataset]

    # Act
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
    assert result.exit_code == 1, result.output
    assert "1 of the requested EGA datasets were skipped, see the warnings above: EGAD00010000500" in result.output
    assert set(Graph().parse("output.ttl").subjects(RDF.type, DCAT.Dataset)) == {DATASET_URI}


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_skips_dataset_without_accession_id(
    fetch_ega_datasets, default_ega_dataset, isolated_cli_runner, caplog
):
    """Without an accession ID, datasets would get the same URI, so such a dataset is skipped."""
    # Arrange
    fetch_ega_datasets.return_value = [{**default_ega_dataset, "accession_id": None}, default_ega_dataset]

    # Act
    with caplog.at_level(logging.WARNING):
        result = _run_map_ega_to_rdf(isolated_cli_runner, EGA_EXAMPLE_CONFIG)

    # Assert
    assert result.exit_code == 1, result.output
    assert "skipped, see the warnings above: (no accession ID)" in result.output
    graph = Graph().parse("output.ttl")
    assert set(graph.subjects(RDF.type, DCAT.Dataset)) == {DATASET_URI}
    assert "Skipping an EGA dataset: EGA dataset None has no accession_id" in caplog.text


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_keeps_dataset_with_unparsable_file_size_and_links_remaining_distributions(
    fetch_ega_datasets, default_ega_dataset, isolated_cli_runner
):
    """The BIN files have no usable size, so only the TXT Distribution is kept, and the dataset links exactly that."""
    # Arrange
    for ega_file in default_ega_dataset["files"]:
        ega_file["filesize"] = "abc"
    default_ega_dataset["files"].append({"accession_id": "EGAF00000000003", "filesize": 500, "extension": "vcf"})
    fetch_ega_datasets.return_value = [default_ega_dataset]

    # Act
    result = _run_map_ega_to_rdf(isolated_cli_runner, EGA_EXAMPLE_CONFIG)

    # Assert
    assert result.exit_code == 0, result.output
    graph = Graph().parse("output.ttl")
    assert set(graph.subjects(RDF.type, DCAT.Distribution)) == {TXT_DISTRIBUTION_URI}
    assert set(graph.objects(DATASET_URI, DCAT.distribution)) == {TXT_DISTRIBUTION_URI}
