import logging
from typing import Dict, List, Union

from fairclient.fdpclient import FDPClient
from fairclient.sparqlclient import FDPSPARQLClient
from fairclient.utils import add_or_update_dataset
from rdflib import DCTERMS

logger = logging.getLogger(__name__)

class FDPOutput:
    def __init__(self, config: Dict, fdp: str, fdp_username: str, fdp_password: str,
                 catalog_uri: Union[str, None]=None,
                 sparql: Union[str, None]=None):
        self.config = config
        self.fdp = fdp

        self.fdpclient = FDPClient(self.fdp, fdp_username, fdp_password)

        self.sparqlclient = None
        if sparql:
            self.sparqlclient = FDPSPARQLClient(sparql)


        self.catalog_uri = catalog_uri
        if not self.catalog_uri:
            self.catalog_uri = self.config.get('catalog', None)
        if not self.catalog_uri:
            raise ValueError("FDP Error: No catalog URI set to push to")

    def push_to_fdp(self, input_obj: Dict[str, List[Dict]]):
        dataset_obj = input_obj['dataset']
        for dataset in dataset_obj:
            graph = dataset['model_object'].to_graph(dataset['uri'])

            # This is FDP specific: Dataset points back to the Catalog
            graph.add((dataset['uri'], DCTERMS.isPartOf, self.catalog_uri))
            logger.debug("Going to push %s to FDP", dataset['model_object'].title)
            try:
                add_or_update_dataset(graph, self.fdpclient, dataset['model_object'].identifier,
                                      self.catalog_uri, self.sparqlclient)
            except Exception as e:
                logger.warning("Error pushing dataset to FDP: %s", e)
