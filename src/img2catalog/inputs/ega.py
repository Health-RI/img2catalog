import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

def fetch_ega_dataset(dataset_id: str, api_url: str) -> Dict:
    response = requests.get(f"{api_url}/datasets/{dataset_id}", timeout=30)
    response.raise_for_status()

    return response.json()


def fetch_ega_datasets(dataset_ids: List[str], api_url: str) -> List[Dict]:
    datasets = []
    for dataset_id in dataset_ids:
        try:
            datasets.append(fetch_ega_dataset(dataset_id, api_url))
        except requests.RequestException as e:
            logger.warning("Error fetching EGA dataset %s: %s", dataset_id, e)

    return datasets

if __name__ == "__main__":
    print(fetch_ega_dataset("EGAD00000000001", "https://metadata.ega-archive.org"))
    print(fetch_ega_datasets(["EGAD00000000001", "EGAD00000000002", "EGAD00000000003"], "https://metadata.ega-archive.org"))