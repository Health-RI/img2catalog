import logging
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


def fetch_ega_dataset(dataset_id: str, api_url: str) -> Dict:
    response = requests.get(f"{api_url}/datasets/{dataset_id}", timeout=30)
    response.raise_for_status()

    return response.json()


def fetch_ega_dacs(dataset_id: str, api_url: str) -> List[Dict]:
    """Fetch the Data Access Committees (DACs) that control access to an EGA dataset."""
    response = requests.get(f"{api_url}/datasets/{dataset_id}/dacs", timeout=30)
    response.raise_for_status()

    return response.json()


def fetch_ega_datasets(dataset_ids: List[str], api_url: str) -> List[Dict]:
    datasets = []
    for dataset_id in dataset_ids:
        try:
            dataset = fetch_ega_dataset(dataset_id, api_url)
        except requests.RequestException as e:
            logger.warning("Error fetching EGA dataset %s: %s", dataset_id, e)
            continue

        try:
            dataset["dacs"] = fetch_ega_dacs(dataset_id, api_url)
        except requests.RequestException as e:
            logger.warning("Error fetching DACs for EGA dataset %s: %s", dataset_id, e)
            dataset["dacs"] = []

        datasets.append(dataset)

    return datasets
