import pathlib
from unittest.mock import patch

from img2catalog.cli_app import cli_click

EGA_EXAMPLE_CONFIG = pathlib.Path(__file__).parents[2] / "examples" / "ega" / "example_config.toml"


@patch("img2catalog.cli_app.fetch_ega_datasets")
def test_ega_cli_fails_when_no_dataset_could_be_fetched(fetch_ega_datasets, isolated_cli_runner):
    """A run that fetched nothing must not look like a success."""
    # Arrange
    fetch_ega_datasets.return_value = []

    # Act
    result = isolated_cli_runner.invoke(
        cli_click,
        ["-c", str(EGA_EXAMPLE_CONFIG), "ega", "-a", "EGAD00001005083", "map-ega-hriv2", "rdf", "-o", "output.ttl"],
    )

    # Assert
    assert result.exit_code != 0
    assert "None of the requested EGA datasets could be fetched" in result.output
    assert not pathlib.Path("output.ttl").exists()
