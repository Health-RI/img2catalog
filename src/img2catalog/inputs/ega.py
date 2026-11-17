import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

HTTP_NOT_FOUND = 404


def fetch_ega_dataset(dataset_id: str, api_url: str) -> Dict:
    response = requests.get(f"{api_url}/datasets/{dataset_id}", timeout=30)
    response.raise_for_status()

    return response.json()


def _fetch_ega_dataset_resource(dataset_id: str, api_url: str, resource: str) -> List[Dict]:
    """Fetch related resources of an EGA dataset; Not Found means the dataset has none of them."""
    response = requests.get(f"{api_url}/datasets/{dataset_id}/{resource}", timeout=30)
    if response.status_code == HTTP_NOT_FOUND:
        # Not an error, but visible: if EGA stops serving a resource, every dataset would silently lose it
        logger.warning(
            "EGA dataset %s has no %s (Not Found: %s), so it is mapped without them", dataset_id, resource, response.url
        )
        return []
    response.raise_for_status()

    return response.json()


def fetch_ega_dacs(dataset_id: str, api_url: str) -> List[Dict]:
    """Fetch the Data Access Committees (DACs) that control access to an EGA dataset."""
    return _fetch_ega_dataset_resource(dataset_id, api_url, "dacs")


def fetch_ega_files(dataset_id: str, api_url: str) -> List[Dict]:
    """Fetch the files that together form an EGA dataset."""
    return _fetch_ega_dataset_resource(dataset_id, api_url, "files")


def fetch_ega_studies(dataset_id: str, api_url: str) -> List[Dict]:
    """Fetch the studies an EGA dataset belongs to, which hold the PubMed IDs of its publications."""
    return _fetch_ega_dataset_resource(dataset_id, api_url, "studies")


def _fetch_complete_ega_dataset(dataset_id: str, api_url: str) -> Optional[Dict]:
    """Fetch an EGA dataset with its DACs, files and studies, or None when any of them could not be fetched."""
    try:
        dataset = fetch_ega_dataset(dataset_id, api_url)
    except requests.RequestException as e:
        logger.error("Error fetching EGA dataset %s, so it is left out: %s", dataset_id, e)
        return None

    for key, label, fetch in (
        ("dacs", "DACs", fetch_ega_dacs),
        ("files", "files", fetch_ega_files),
        ("studies", "studies", fetch_ega_studies),
    ):
        try:
            dataset[key] = fetch(dataset_id, api_url)
        except requests.RequestException as e:
            logger.error("Error fetching %s for EGA dataset %s, so it is left out: %s", label, dataset_id, e)
            return None

    return dataset


def fetch_ega_datasets(dataset_ids: List[str], api_url: str) -> List[Dict]:
    """Fetch EGA datasets, each with its DACs, files and studies.

    A dataset is left out, with an error logged, when it or any of its DACs, files or studies cannot be fetched.
    Mapping it without them would give a degraded record, which a push to the FDP would use to overwrite a complete one.
    """
    datasets = []
    for dataset_id in dataset_ids:
        dataset = _fetch_complete_ega_dataset(dataset_id, api_url)
        if dataset is not None:
            datasets.append(dataset)

    return datasets
