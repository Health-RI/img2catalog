import logging

import pytest
import requests

from img2catalog.inputs.ega import (
    fetch_ega_dacs,
    fetch_ega_dataset,
    fetch_ega_datasets,
    fetch_ega_files,
    fetch_ega_studies,
)

API_URL = "https://metadata.ega-archive.org"


def test_fetch_ega_dataset_returns_json(requests_mock, default_ega_dataset):
    # Arrange
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083", json=default_ega_dataset)

    # Act
    result = fetch_ega_dataset("EGAD00001005083", API_URL)

    # Assert
    assert result == default_ega_dataset


def test_fetch_ega_dataset_raises_on_404(requests_mock):
    # Arrange
    requests_mock.get(f"{API_URL}/datasets/EGAD00000000000", status_code=404)

    # Act & Assert
    with pytest.raises(requests.HTTPError):
        fetch_ega_dataset("EGAD00000000000", API_URL)


def test_fetch_ega_dacs_returns_json(requests_mock, default_ega_dataset):
    # Arrange
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/dacs", json=default_ega_dataset["dacs"])

    # Act
    result = fetch_ega_dacs("EGAD00001005083", API_URL)

    # Assert
    assert result == default_ega_dataset["dacs"]


def test_fetch_ega_files_returns_json(requests_mock, default_ega_dataset):
    # Arrange
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/files", json=default_ega_dataset["files"])

    # Act
    result = fetch_ega_files("EGAD00001005083", API_URL)

    # Assert
    assert result == default_ega_dataset["files"]


def test_fetch_ega_studies_returns_json(requests_mock, default_ega_dataset):
    # Arrange
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/studies", json=default_ega_dataset["studies"])

    # Act
    result = fetch_ega_studies("EGAD00001005083", API_URL)

    # Assert
    assert result == default_ega_dataset["studies"]


def test_fetch_ega_datasets_returns_all_on_success(requests_mock, default_ega_dataset):
    # Arrange
    dacs = default_ega_dataset.pop("dacs")
    files = default_ega_dataset.pop("files")
    studies = default_ega_dataset.pop("studies")
    other_dataset = {**default_ega_dataset, "accession_id": "EGAD00001005084"}
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083", json=default_ega_dataset)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005084", json=other_dataset)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/dacs", json=dacs)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005084/dacs", json=[])
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/files", json=files)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005084/files", json=[])
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/studies", json=studies)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005084/studies", json=[])

    # Act
    result = fetch_ega_datasets(["EGAD00001005083", "EGAD00001005084"], API_URL)

    # Assert
    assert result == [
        {**default_ega_dataset, "dacs": dacs, "files": files, "studies": studies},
        {**other_dataset, "dacs": [], "files": [], "studies": []},
    ]


def test_fetch_ega_datasets_skips_failed_dataset(requests_mock, default_ega_dataset):
    # Arrange
    dacs = default_ega_dataset.pop("dacs")
    files = default_ega_dataset.pop("files")
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083", json=default_ega_dataset)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/dacs", json=dacs)
    studies = default_ega_dataset.pop("studies")
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/files", json=files)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/studies", json=studies)
    requests_mock.get(f"{API_URL}/datasets/EGAD00000000000", status_code=404)

    # Act
    result = fetch_ega_datasets(["EGAD00001005083", "EGAD00000000000"], API_URL)

    # Assert
    assert result == [{**default_ega_dataset, "dacs": dacs, "files": files, "studies": studies}]


@pytest.mark.parametrize(
    ("failing_resource", "label"),
    [("dacs", "DACs"), ("files", "files"), ("studies", "studies")],
)
def test_fetch_ega_datasets_skips_dataset_when_a_sub_resource_fails(
    requests_mock, default_ega_dataset, caplog, failing_resource, label
):
    """A dataset without its DACs, files or studies would be a degraded record, so it is left out entirely."""
    # Arrange
    sub_resources = {key: default_ega_dataset.pop(key) for key in ("dacs", "files", "studies")}
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083", json=default_ega_dataset)
    for key, value in sub_resources.items():
        if key == failing_resource:
            requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/{key}", status_code=500)
        else:
            requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/{key}", json=value)

    # Act
    with caplog.at_level(logging.ERROR):
        result = fetch_ega_datasets(["EGAD00001005083"], API_URL)

    # Assert
    assert result == []
    assert f"Error fetching {label} for EGA dataset EGAD00001005083, so it is left out" in caplog.text


def test_fetch_ega_datasets_keeps_complete_datasets_next_to_a_failed_one(requests_mock, default_ega_dataset):
    # Arrange
    sub_resources = {key: default_ega_dataset.pop(key) for key in ("dacs", "files", "studies")}
    other_dataset = {**default_ega_dataset, "accession_id": "EGAD00001005084"}
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083", json=default_ega_dataset)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005084", json=other_dataset)
    for key, value in sub_resources.items():
        requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/{key}", json=value)
        requests_mock.get(f"{API_URL}/datasets/EGAD00001005084/{key}", status_code=500)

    # Act
    result = fetch_ega_datasets(["EGAD00001005083", "EGAD00001005084"], API_URL)

    # Assert
    assert result == [{**default_ega_dataset, **sub_resources}]
