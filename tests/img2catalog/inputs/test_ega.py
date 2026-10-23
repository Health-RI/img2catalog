import pytest
import requests

from img2catalog.inputs.ega import fetch_ega_dacs, fetch_ega_dataset, fetch_ega_datasets, fetch_ega_files

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


def test_fetch_ega_datasets_returns_all_on_success(requests_mock, default_ega_dataset):
    # Arrange
    dacs = default_ega_dataset.pop("dacs")
    files = default_ega_dataset.pop("files")
    other_dataset = {**default_ega_dataset, "accession_id": "EGAD00001005084"}
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083", json=default_ega_dataset)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005084", json=other_dataset)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/dacs", json=dacs)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005084/dacs", json=[])
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/files", json=files)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005084/files", json=[])

    # Act
    result = fetch_ega_datasets(["EGAD00001005083", "EGAD00001005084"], API_URL)

    # Assert
    assert result == [
        {**default_ega_dataset, "dacs": dacs, "files": files},
        {**other_dataset, "dacs": [], "files": []},
    ]


def test_fetch_ega_datasets_skips_failed_dataset(requests_mock, default_ega_dataset):
    # Arrange
    dacs = default_ega_dataset.pop("dacs")
    files = default_ega_dataset.pop("files")
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083", json=default_ega_dataset)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/dacs", json=dacs)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/files", json=files)
    requests_mock.get(f"{API_URL}/datasets/EGAD00000000000", status_code=404)

    # Act
    result = fetch_ega_datasets(["EGAD00001005083", "EGAD00000000000"], API_URL)

    # Assert
    assert result == [{**default_ega_dataset, "dacs": dacs, "files": files}]


def test_fetch_ega_datasets_keeps_dataset_when_dacs_fail(requests_mock, default_ega_dataset, caplog):
    # Arrange
    default_ega_dataset.pop("dacs")
    files = default_ega_dataset.pop("files")
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083", json=default_ega_dataset)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/dacs", status_code=500)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/files", json=files)

    # Act
    result = fetch_ega_datasets(["EGAD00001005083"], API_URL)

    # Assert
    assert result == [{**default_ega_dataset, "dacs": [], "files": files}]
    assert "Error fetching DACs for EGA dataset EGAD00001005083" in caplog.text


def test_fetch_ega_datasets_keeps_dataset_when_files_fail(requests_mock, default_ega_dataset, caplog):
    # Arrange
    dacs = default_ega_dataset.pop("dacs")
    default_ega_dataset.pop("files")
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083", json=default_ega_dataset)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/dacs", json=dacs)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083/files", status_code=500)

    # Act
    result = fetch_ega_datasets(["EGAD00001005083"], API_URL)

    # Assert
    assert result == [{**default_ega_dataset, "dacs": dacs, "files": []}]
    assert "Error fetching files for EGA dataset EGAD00001005083" in caplog.text
