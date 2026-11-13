import logging
from typing import Dict, List, Optional, Union

from fairclient.fdpclient import FDPClient
from fairclient.sparqlclient import FDPSPARQLClient
from fairclient.utils import add_or_update_dataset
from rdflib import DCAT, DCTERMS, RDF, Graph, URIRef
from sempyro import LiteralField

logger = logging.getLogger(__name__)

# URIs that img2catalog gives to mapped objects before they get a URI in the FDP
INTERNAL_URI_PREFIX = "http://img2catalog.internal/"


def remove_internal_distribution_links(graph: Graph, dataset_uri: URIRef) -> None:
    """Remove the links of a Dataset to Distributions that only have an internal img2catalog URI.

    Distributions are not pushed to the FDP (yet), so these links would not resolve in the FDP. Links to
    Distributions with an actual URI are kept.
    """
    for distribution in list(graph.objects(dataset_uri, DCAT.distribution)):
        if str(distribution).startswith(INTERNAL_URI_PREFIX):
            graph.remove((dataset_uri, DCAT.distribution, distribution))


def get_identifier_value(identifier: Union[str, LiteralField, None]) -> Optional[str]:
    """Return the text of a Dataset identifier, which is matched to the identifiers of the datasets in the FDP.

    A mapping can set the identifier as text or as a LiteralField (e.g. EGA); the FDP is queried with the text.
    """
    if isinstance(identifier, LiteralField):
        return identifier.value
    return identifier


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

    def publish_if_draft(self, fdp_uri: URIRef) -> None:
        """Publish an existing record in the FDP when it is still a draft.

        Updating a record keeps its state, and the FDP refuses to publish a record that is already published. A record
        stays a draft when publishing it failed when it was created; without publishing it, it would never be shown.
        """
        try:
            response = self.fdpclient.session.get(
                f"{fdp_uri}/meta", headers={"Accept": "application/json"}, timeout=self.fdpclient.timeout
            )
            response.raise_for_status()
            state = (response.json().get("state") or {}).get("current")
        except Exception as e:
            logger.warning("Could not check if dataset %s is published in the FDP: %s", fdp_uri, e)
            return

        if state == "DRAFT":
            logger.info("Publishing dataset %s, which was still a draft in the FDP", fdp_uri)
            self.fdpclient.publish_record(fdp_uri)

    def push_to_fdp(self, input_obj: Dict[str, List[Dict]]) -> None:
        """Push Datasets to a FAIR Data Point

        A Dataset already in the FDP catalog, with the same identifier, is updated instead of added again, so
        rerunning a push keeps the datasets in the FDP up to date. This needs the SPARQL endpoint of the FDP.

        Parameters
        ----------
        input_obj: Dict[str, List[Dict]]
            Dictionary with a list of Health-RI concept objects per concept type

        """
        if not self.sparqlclient:
            logger.warning(
                "No SPARQL endpoint set: existing datasets in the FDP cannot be found, so every push adds them again"
            )

        dataset_obj = input_obj["dataset"]
        for dataset in dataset_obj:
            graph = dataset["model_object"].to_graph(dataset["uri"])

            # This is FDP specific: Dataset points back to the Catalog
            graph.add((dataset["uri"], DCTERMS.isPartOf, self.catalog_uri))
            remove_internal_distribution_links(graph, dataset["uri"])
            identifier = get_identifier_value(dataset["model_object"].identifier)
            logger.debug("Going to push %s to FDP", dataset["model_object"].title)
            try:
                result = add_or_update_dataset(graph, self.fdpclient, identifier, self.catalog_uri, self.sparqlclient)
                # A created dataset is published by fairclient (it returns its URI); an updated one keeps its state.
                # The updated graph has the subject of the existing dataset in the FDP.
                if not isinstance(result, URIRef):
                    self.publish_if_draft(graph.value(predicate=RDF.type, object=DCAT.Dataset, any=False))
            except ValueError as e:
                # The FDP catalog holds more than one dataset with this identifier, e.g. from pushes without SPARQL
                logger.warning(
                    "Error pushing dataset %s to FDP: %s. Remove the duplicate datasets with this identifier from the "
                    "FDP catalog to update it again",
                    identifier,
                    e,
                )
            except Exception as e:
                logger.warning("Error pushing dataset %s to FDP: %s", identifier, e)
