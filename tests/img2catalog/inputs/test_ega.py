import pytest
import requests

from img2catalog.inputs.ega import fetch_ega_dataset, fetch_ega_datasets

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


def test_fetch_ega_datasets_returns_all_on_success(requests_mock, default_ega_dataset):
    # Arrange
    other_dataset = {**default_ega_dataset, "dataset_id": "EGAD00001005084"}
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083", json=default_ega_dataset)
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005084", json=other_dataset)

    # Act
    result = fetch_ega_datasets(["EGAD00001005083", "EGAD00001005084"], API_URL)

    # Assert
    assert result == [default_ega_dataset, other_dataset]


def test_fetch_ega_datasets_skips_failed_dataset(requests_mock, default_ega_dataset):
    # Arrange
    requests_mock.get(f"{API_URL}/datasets/EGAD00001005083", json=default_ega_dataset)
    requests_mock.get(f"{API_URL}/datasets/EGAD00000000000", status_code=404)

    # Act
    result = fetch_ega_datasets(["EGAD00001005083", "EGAD00000000000"], API_URL)

    # Assert
    assert result == [default_ega_dataset]
