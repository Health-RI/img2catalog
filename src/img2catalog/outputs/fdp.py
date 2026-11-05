import logging
from typing import Dict, List, Optional, Union

from fairclient.fdpclient import FDPClient
from fairclient.sparqlclient import FDPSPARQLClient
from fairclient.utils import add_or_update_dataset, rewrite_graph_subject
from rdflib import DCAT, DCTERMS, URIRef

logger = logging.getLogger(__name__)


class FDPOutput:
    """Output class that handles output to a FAIR Data Point (FDP)

    Parameters
    ----------
    config : Dict
        Dictionary containing the contents of the configuration
    fdp : str
        URL to the FDP to push to
    fdp_username: str
        Username for the FDP to push to
    fdp_password: str
        Password for the FDP to push to
    catalog_uri: Union[str, None]
        URI for the catalog on the FDP to add the datasets under
    sparql: Union[str, None]
        URL to the SparQL endpoint

    """

    def __init__(
        self,
        config: Dict,
        fdp: str,
        fdp_username: str,
        fdp_password: str,
        catalog_uri: Union[str, None] = None,
        sparql: Union[str, None] = None,
    ):
        self.config = config
        self.fdp = fdp

        self.fdpclient = FDPClient(self.fdp, fdp_username, fdp_password)

        self.sparqlclient = None
        if sparql:
            self.sparqlclient = FDPSPARQLClient(sparql)

        self.catalog_uri = catalog_uri
        if not self.catalog_uri:
            self.catalog_uri = self.config["fdp"].get("catalog", None) if "fdp" in self.config else None
        if not self.catalog_uri:
            raise ValueError("FDP Error: No catalog URI set to push to")
        if isinstance(self.catalog_uri, str):
            self.catalog_uri = URIRef(self.catalog_uri)

    def push_to_fdp(self, input_obj: Dict[str, List[Dict]]) -> None:
        """Push Datasets, and their Distributions if present, to a FAIR Data Point

        Parameters
        ----------
        input_obj: Dict[str, List[Dict]]
            Dictionary with a list of Health-RI concept objects per concept type

        """
        dataset_obj = input_obj["dataset"]
        distribution_obj = input_obj.get("distribution", [])
        for dataset in dataset_obj:
            graph = dataset["model_object"].to_graph(dataset["uri"])
            distributions = [
                distribution for distribution in distribution_obj if distribution["dataset_uri"] == dataset["uri"]
            ]

            # This is FDP specific: Dataset points back to the Catalog
            graph.add((dataset["uri"], DCTERMS.isPartOf, self.catalog_uri))
            # The FDP links Distributions to their Dataset itself, from the Distribution's isPartOf
            graph.remove((dataset["uri"], DCAT.distribution, None))
            logger.debug("Going to push %s to FDP", dataset["model_object"].title)
            try:
                result = add_or_update_dataset(
                    graph, self.fdpclient, dataset["model_object"].identifier, self.catalog_uri, self.sparqlclient
                )
            except Exception as e:
                logger.warning("Error pushing dataset to FDP: %s", e)
                continue

            if not distributions:
                continue

            # A created dataset returns its new FDP URI, an updated dataset has to be looked up
            fdp_dataset_uri = result if isinstance(result, URIRef) else self._find_dataset_subject(dataset)
            if not fdp_dataset_uri:
                logger.warning("Could not find FDP dataset of %s, skipping its distributions", dataset["uri"])
                continue

            for distribution in distributions:
                self._push_distribution(distribution, URIRef(fdp_dataset_uri))

    def _find_dataset_subject(self, dataset: Dict) -> Optional[str]:
        if not self.sparqlclient:
            return None
        return self.sparqlclient.find_subject(dataset["model_object"].identifier, self.catalog_uri)

    def _find_distribution_subject(self, fdp_dataset_uri: URIRef, distribution_format: URIRef) -> Optional[str]:
        """Find the FDP Distribution of a Dataset with the given format, which identifies a Distribution of a Dataset"""
        query = f"""PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?subject
WHERE {{
    ?subject dcterms:isPartOf <{fdp_dataset_uri}> .
    ?subject dcterms:format <{distribution_format}> .
}}"""
        self.sparqlclient.sparql.setQuery(query)
        results = self.sparqlclient.sparql.queryAndConvert()["results"]["bindings"]

        if len(results) == 0:
            return None
        if len(results) > 1:
            raise ValueError("More than one distribution with the same format in FDP dataset")
        if results[0]["subject"]["type"].casefold() != "uri":
            raise TypeError("Incorrect result type for subject in FDP")

        return results[0]["subject"]["value"]

    def _push_distribution(self, distribution: Dict, fdp_dataset_uri: URIRef) -> None:
        """Update the FDP Distribution with the same format in the Dataset, or create it when there is none"""
        graph = distribution["model_object"].to_graph(distribution["uri"])
        graph.add((distribution["uri"], DCTERMS.isPartOf, fdp_dataset_uri))

        try:
            fdp_subject_uri = None
            if self.sparqlclient:
                fdp_subject_uri = self._find_distribution_subject(
                    fdp_dataset_uri, URIRef(str(distribution["model_object"].format))
                )

            if fdp_subject_uri:
                logger.debug("Updating distribution %s in FDP", fdp_subject_uri)
                rewrite_graph_subject(graph, distribution["uri"], fdp_subject_uri)
                self.fdpclient.update_serialized(fdp_subject_uri, graph)
            else:
                self.fdpclient.create_and_publish("distribution", graph)
        except Exception as e:
            logger.warning("Error pushing distribution to FDP: %s", e)
