import logging
from typing import Dict, List

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
        logger.debug("EGA dataset %s has no %s", dataset_id, resource)
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


def fetch_ega_datasets(dataset_ids: List[str], api_url: str) -> List[Dict]:
    """Fetch EGA datasets with their DACs, files and studies.

    A dataset of which any part cannot be fetched is skipped. Otherwise its incomplete metadata would replace the
    complete metadata of the dataset in the FDP when pushing it again.
    """
    datasets = []
    for dataset_id in dataset_ids:
        try:
            dataset = fetch_ega_dataset(dataset_id, api_url)
            dataset["dacs"] = fetch_ega_dacs(dataset_id, api_url)
            dataset["files"] = fetch_ega_files(dataset_id, api_url)
            dataset["studies"] = fetch_ega_studies(dataset_id, api_url)
        except requests.RequestException as e:
            logger.warning("Error fetching EGA dataset %s, skipping it: %s", dataset_id, e)
            continue

        datasets.append(dataset)

    return datasets
