import json
import logging
from typing import Dict, List, Optional, Union

from fairclient.fdpclient import FDPClient
from fairclient.sparqlclient import FDPSPARQLClient
from fairclient.utils import rewrite_graph_subject
from rdflib import DCAT, DCTERMS, RDF, Graph, Namespace, URIRef
from sempyro import LiteralField

logger = logging.getLogger(__name__)

FDP_O = Namespace("https://w3id.org/fdp/fdp-o#")

# URIs that img2catalog gives to mapped objects before they get a URI in the FDP
INTERNAL_URI_PREFIX = "http://img2catalog.internal/"

# The FDP links a parent record to its children (e.g. a Catalog to its Datasets) when a child is pushed. Updating the
# parent replaces its metadata, which removes these links, so they are kept when updating a record.
CHILD_LINKS = {"catalog": DCAT.dataset, "dataset": DCAT.distribution}


def remove_internal_distribution_links(graph: Graph, dataset_uri: URIRef) -> None:
    """Remove the links of a Dataset to Distributions that only have an internal img2catalog URI.

    The FDP links a Dataset to the Distributions pushed into it, so these links would not resolve in the FDP. Links to
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


def _sparql_string(value: str) -> str:
    """Quote a text as a SPARQL string literal."""
    return json.dumps(value, ensure_ascii=False)


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
        URI of the catalog in the FDP to push to. When the mapping has a Catalog, this catalog is updated with it;
        without it, the Catalog is found in the FDP by its title, or created.
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
        if isinstance(self.catalog_uri, str):
            self.catalog_uri = URIRef(self.catalog_uri)

    def push_to_fdp(self, input_obj: Dict[str, List[Dict]]) -> None:
        """Push the Catalog, Datasets and Distributions to a FAIR Data Point

        The Catalog is pushed first, then the Datasets into it, then the Distributions into their Dataset. Contact
        points (vcard:Kind) and other nested classes are pushed as part of the record they belong to.

        A record already in the FDP is updated instead of added again, so rerunning a push keeps the FDP up to date: a
        Dataset is found by its identifier within the Catalog, a Distribution by its format within its Dataset, and a
        Catalog by its title (unless its URI is given). This needs the SPARQL endpoint of the FDP.

        Parameters
        ----------
        input_obj: Dict[str, List[Dict]]
            Dictionary with a list of Health-RI concept objects per concept type

        """
        if not self.sparqlclient:
            logger.warning(
                "No SPARQL endpoint set: existing records in the FDP cannot be found, so every push adds them again"
            )

        catalog_uri = self.push_catalog(input_obj.get("catalog") or [])

        fdp_datasets = {}
        for dataset in input_obj["dataset"]:
            fdp_uri = self.push_dataset(dataset, catalog_uri)
            if fdp_uri is not None:
                fdp_datasets[dataset["uri"]] = fdp_uri

        for distribution in input_obj.get("distribution") or []:
            dataset_uri = fdp_datasets.get(distribution["dataset_uri"])
            if dataset_uri is None:
                logger.warning(
                    "Skipping Distribution %s, as its Dataset was not pushed to the FDP", distribution["uri"]
                )
                continue
            self.push_distribution(distribution, dataset_uri)

    def push_catalog(self, catalogs: List[Dict]) -> URIRef:
        """Push the mapped Catalog, and return the URI of the catalog in the FDP to push the Datasets to."""
        if not catalogs:
            if not self.catalog_uri:
                raise ValueError("FDP Error: No catalog URI set to push to")
            return self.catalog_uri
        if len(catalogs) > 1:
            logger.warning("Only the first of %d Catalogs is pushed to the FDP", len(catalogs))

        catalog = catalogs[0]
        graph = catalog["model_object"].to_graph(catalog["uri"])
        # The FDP links the Catalog to the Datasets pushed into it
        graph.remove((catalog["uri"], DCAT.dataset, None))
        root = self.get_fdp_root()
        graph.add((catalog["uri"], DCTERMS.isPartOf, root))

        title = str(next(iter(graph.objects(catalog["uri"], DCTERMS.title)), ""))
        try:
            fdp_uri = self.catalog_uri or self.find_catalog(title, root)
            return self.push_record("catalog", graph, catalog["uri"], fdp_uri)
        except Exception as e:
            if not self.catalog_uri:
                raise ValueError(f"FDP Error: Could not push catalog {title!r} to the FDP: {e}") from e
            logger.warning(
                "Error updating catalog %s in the FDP, pushing the datasets into it: %s", self.catalog_uri, e
            )
            return self.catalog_uri

    def push_dataset(self, dataset: Dict, catalog_uri: URIRef) -> Optional[URIRef]:
        """Push a Dataset into the catalog in the FDP, and return its URI in the FDP (None when it failed)."""
        graph = dataset["model_object"].to_graph(dataset["uri"])
        # This is FDP specific: Dataset points back to the Catalog
        graph.add((dataset["uri"], DCTERMS.isPartOf, catalog_uri))
        remove_internal_distribution_links(graph, dataset["uri"])
        identifier = get_identifier_value(dataset["model_object"].identifier)
        logger.debug("Going to push %s to FDP", dataset["model_object"].title)
        try:
            fdp_uri = None
            if self.sparqlclient and identifier:
                fdp_uri = self.sparqlclient.find_subject(identifier, catalog_uri)
            return self.push_record("dataset", graph, dataset["uri"], fdp_uri)
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
        return None

    def push_distribution(self, distribution: Dict, dataset_uri: URIRef) -> Optional[URIRef]:
        """Push a Distribution into its Dataset in the FDP, and return its URI in the FDP (None when it failed)."""
        graph = distribution["model_object"].to_graph(distribution["uri"])
        graph.add((distribution["uri"], DCTERMS.isPartOf, dataset_uri))
        file_format = getattr(distribution["model_object"], "format", None)
        try:
            fdp_uri = None
            if self.sparqlclient and file_format:
                fdp_uri = self.find_distribution(dataset_uri, URIRef(str(file_format)))
            return self.push_record("distribution", graph, distribution["uri"], fdp_uri)
        except Exception as e:
            logger.warning("Error pushing distribution %s of dataset %s to FDP: %s", file_format, dataset_uri, e)
        return None

    def push_record(self, record_type: str, graph: Graph, subject: URIRef, fdp_uri: Union[str, URIRef, None]) -> URIRef:
        """Create a record in the FDP, or update the existing record with URI fdp_uri, and return its URI."""
        if not fdp_uri:
            created = URIRef(self.fdpclient.create_and_publish(record_type, graph))
            logger.info("Created %s %s in the FDP", record_type, created)
            return created

        fdp_uri = URIRef(fdp_uri)
        rewrite_graph_subject(graph, subject, fdp_uri)
        self.keep_child_links(record_type, fdp_uri, graph)
        self.fdpclient.update_serialized(fdp_uri, graph)
        logger.info("Updated %s %s in the FDP", record_type, fdp_uri)
        # An updated record keeps its state in the FDP
        self.publish_if_draft(fdp_uri)
        return fdp_uri

    def keep_child_links(self, record_type: str, fdp_uri: URIRef, graph: Graph) -> None:
        """Add the links of an existing record to its children in the FDP to the graph it is updated with.

        Otherwise the update removes them, and e.g. the Datasets of a Catalog that are not pushed again would no
        longer be listed in it.
        """
        predicate = CHILD_LINKS.get(record_type)
        if predicate is None:
            return
        try:
            response = self.fdpclient.session.get(
                str(fdp_uri), headers={"Accept": "text/turtle"}, timeout=self.fdpclient.timeout
            )
            response.raise_for_status()
            existing = Graph().parse(data=response.text, format="turtle")
        except Exception as e:
            logger.warning("Could not read the links of %s %s to its children in the FDP: %s", record_type, fdp_uri, e)
            return
        for child in existing.objects(fdp_uri, predicate):
            graph.add((fdp_uri, predicate, child))

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
            logger.warning("Could not check if %s is published in the FDP: %s", fdp_uri, e)
            return

        if state == "DRAFT":
            logger.info("Publishing %s, which was still a draft in the FDP", fdp_uri)
            self.fdpclient.publish_record(fdp_uri)

    def get_fdp_root(self) -> URIRef:
        """Return the URI of the FAIR Data Point itself, which is the parent of its catalogs."""
        try:
            response = self.fdpclient.session.get(self.fdp, headers={"Accept": "text/turtle"}, timeout=30)
            response.raise_for_status()
            root = (
                Graph().parse(data=response.text, format="turtle").value(predicate=RDF.type, object=FDP_O.FAIRDataPoint)
            )
        except Exception as e:
            logger.warning("Could not read the FDP root %s, using its URL: %s", self.fdp, e)
            root = None
        return URIRef(root or self.fdp)

    def _query_subjects(self, query: str) -> List[str]:
        self.sparqlclient.sparql.setQuery(query)
        bindings = self.sparqlclient.sparql.queryAndConvert()["results"]["bindings"]
        return sorted({binding["subject"]["value"] for binding in bindings})

    def find_catalog(self, title: str, root: URIRef) -> Optional[str]:
        """Find the catalog with this title in the FDP."""
        if not self.sparqlclient or not title:
            return None
        subjects = self._query_subjects(
            f"""PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT DISTINCT ?subject
WHERE {{
    ?subject a dcat:Catalog ;
        dcterms:isPartOf <{root}> ;
        dcterms:title ?title .
    FILTER(str(?title) = {_sparql_string(title)})
}}"""
        )
        if len(subjects) > 1:
            raise ValueError(
                f"More than one catalog titled {title!r} in the FDP: {subjects}; give the one to use with -c"
            )
        return subjects[0] if subjects else None

    def find_distribution(self, dataset_uri: URIRef, file_format: URIRef) -> Optional[str]:
        """Find the Distribution of a Dataset in the FDP with this format, which identifies it within the Dataset."""
        subjects = self._query_subjects(
            f"""PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT DISTINCT ?subject
WHERE {{
    ?subject a dcat:Distribution ;
        dcterms:isPartOf <{dataset_uri}> ;
        dcterms:format <{file_format}> .
}}"""
        )
        if len(subjects) > 1:
            raise ValueError(f"More than one distribution with format {file_format} in dataset {dataset_uri}")
        return subjects[0] if subjects else None
