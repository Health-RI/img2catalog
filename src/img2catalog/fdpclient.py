import logging
from typing import Dict, Union
from urllib.parse import urljoin

import requests
from rdflib import DCAT, DCTERMS, RDF, Graph, URIRef
from requests import HTTPError, Response
from sempyro.vcard import VCARD
from SPARQLWrapper import JSON, SPARQLWrapper

logger = logging.getLogger(__name__)

# The FDP client is taken from cedar2fdp


class BasicAPIClient:
    """Basic class for API client"""

    def __init__(self, base_url, headers):
        self.base_url = base_url
        self.headers = headers
        self.session = requests.session()
        self.session.headers.update(self.headers)
        self.ssl_verification = None

    def _call_method(self, method, path, params: Dict = None, data=None) -> Response:
        if method.upper() not in ["GET", "POST", "PUT", "DELETE"]:
            raise ValueError(f"Unsupported method {method}")
        url = urljoin(self.base_url, path)
        response = None
        # try:
        response = self.session.request(method, url, params=params, data=data, verify=self.ssl_verification)

        try:
            response.raise_for_status()
        except HTTPError as e:
            logger.error("%d %s: %s", e.response.status_code, e.response.reason, e.response.text)
            raise e

        return response

    def get(self, path: str, params: Dict = None) -> Response:
        return self._call_method("GET", path, params=params)

    def post(self, path: str, params: Dict = None, data=None) -> Response:
        return self._call_method("POST", path, params=params, data=data)

    def update(self, path: str, params: Dict = None, data=None) -> Response:
        return self._call_method("PUT", path, params=params, data=data)

    def delete(self, path: str, params: Dict = None, data=None) -> Response:
        return self._call_method("DELETE", path, params=params, data=data)


class FDPEndPoints:
    meta = "meta"
    state = f"{meta}/state"
    members = "members"
    expanded = "expanded"


class FDPClient(BasicAPIClient):
    """Client for FAIR Data Point client"""

    def __init__(self, base_url: str, username: str, password: str):
        """Initializes an FDP Client object

        Parameters
        ----------
        base_url : str
            Base URL of the Fair Data Point
        username : str
            username for authentication
        password : str
            password for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        # Don't store password for security reasons (might show up in a stack trace or something)
        # self.password = password
        logger.debug("Logging into FDP %s with user %s", self.base_url, self.username)
        self.__token = self.login_fdp(username, password)
        headers = self.get_headers()
        super().__init__(self.base_url, headers)

    def login_fdp(self, username: str, password: str) -> str:
        """Logs in to a Fair Data Point and retrieves a JWT token

        Parameters
        ----------
        username : str
            username for authentication
        password : str
            password for authentication

        Returns
        -------
        str
            JWT authentication token
        """
        token_response = requests.post(
            f"{self.base_url}/tokens",
            json={"email": username, "password": password},
        )
        token_response.raise_for_status()
        response = token_response.json()
        token = response["token"]
        self.__token = token
        return token

    def get_headers(self) -> Dict:
        return {"Authorization": f"Bearer {self.__token}", "Content-Type": "text/turtle"}

    def _update_session_headers(self):
        self.session.headers.update(self.headers)

    def _change_content_type(self, content_type: str):
        self.headers["Content-Type"] = content_type
        self._update_session_headers()

    def post_serialized(self, resource_type: str, metadata: "Graph") -> requests.Response:
        """Serializes and POSTs a graph to an FDP

        Parameters
        ----------
        resource_type : str
            Type of resource to push (e.g. 'dataset')
        metadata : Graph
            The graph with metadata to be pusshed

        Returns
        -------
        requests.Response
            The response from the FDP
        """
        self._change_content_type("text/turtle")
        path = f"{self.base_url}/{resource_type}"
        logger.debug("Posting metadata to %s", path)
        response = self.post(path=path, data=metadata.serialize(format="turtle"))
        return response

    def update_serialized(self, resource_uri: str, metadata: "Graph") -> requests.Response:
        """Serializes and updates (PUTs) a graph on an FDP

        Parameters
        ----------
        resource_uri : str
            URI to update
        metadata : Graph
            The graph with metadata to be pusshed

        Returns
        -------
        requests.Response
            The response from the FDP
        """
        self._change_content_type("text/turtle")
        logger.debug("Putting metadata to %s", resource_uri)
        response = self.update(path=resource_uri, data=metadata.serialize(format="turtle"))
        return response

    def get_data(self, path: str) -> requests.Response:
        response = self.get(path=path)
        return response

    def delete_record(self, path: str) -> requests.Response:
        response = self.delete(path=path)
        return response

    def publish_record(self, record_url: str):
        """Changes the status of an FDP record to "Published"

        Parameters
        ----------
        record_url : str
            URL of the record that is to be published
        """
        self._change_content_type("application/json")
        path = f"{record_url}/{FDPEndPoints.state}"
        data = '{"current": "PUBLISHED"}'
        self.update(path=path, data=data)

    def create_and_publish(self, resource_type: str, metadata: "Graph") -> URIRef:
        """Creates and publishes a record in the FDP

        Parameters
        ----------
        resource_type : str
            Type of record to publish (e.g. Catalog, Distribution, Dataset)
        metadata : Graph
            The metadata to be published

        Returns
        -------
        URIRef
            URI of (subject of) published dataset
        """
        post_response = self.post_serialized(resource_type=resource_type, metadata=metadata)

        # FDP will return a 201 status code with the new identifier of the published record
        fdp_subject = URIRef(post_response.headers["Location"])

        # Change status to 'published' so that metadata shows in catalog
        logger.debug("New FDP subject: %s", fdp_subject)
        self.publish_record(fdp_subject)

        return fdp_subject


def remove_node_from_graph(node, graph: Graph):
    """Completely removes a node and all references to it from a graph

    Parameters
    ----------
    node : ...
        Node to be removed
    graph : Graph
        Graph to remove it from
    """
    # Remove all triples with the node as a subject and an object
    graph.remove((node, None, None))
    graph.remove((None, None, node))


class FDPSPARQLClient:
    """Simple SPARQL client to query a SPARQL endpoint of (reference) FAIR Data Point."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint

        self.sparql = SPARQLWrapper(endpoint)
        self.sparql.setReturnFormat(JSON)

    def find_subject(self, identifier, catalog):
        query = f"""PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT *
WHERE {{
    ?subject dcterms:identifier "{identifier}" .
    ?subject dcterms:isPartOf <{catalog}> .
}}"""
        self.sparql.setQuery(query)
        results = self.sparql.queryAndConvert()["results"]["bindings"]

        if len(results) == 0:
            # No result found
            return None
        elif len(results) > 1:
            raise ValueError("More than one result for SPARQL query")
        else:
            if not results[0]["subject"]["type"].casefold() == "uri":
                raise TypeError("Incorrect result type for subject in FDP")
            return results[0]["subject"]["value"]


def prepare_dataset_graph_for_fdp(dataset_graph: Graph, catalog_uri: URIRef):
    """Mangles the graph of a dataset in such a way a FDP can take it

    Adds the isPartOf property to point back to parent catalog and removes some blind VCard nodes
    that it doens't seem to like.

    Parameters
    ----------
    dataset_graph : Graph
        RDFlib graph of the DCAT Dataset
    catalog_uri : URIRef
        URIRef of the Catalog to point back to

    Raises
    ------
    TypeError
        if the catalog_uri is not a URIRef (e.g. it is a string)
    """
    if type(catalog_uri) is not URIRef:
        raise TypeError("catalog_uri is not a URIRef")

    # For each dataset, find the creator node. If it is a VCard, get rid of it
    for dataset in dataset_graph.subjects(RDF.type, DCAT.Dataset):
        creator_node = dataset_graph.value(subject=dataset, predicate=DCTERMS.creator, any=False)
        if creator_node:
            if dataset_graph.value(subject=creator_node, predicate=RDF.type, any=False) == VCARD.VCard:
                remove_node_from_graph(creator_node, dataset_graph)

        contactpoint_node = dataset_graph.value(subject=dataset, predicate=DCAT.contactPoint, any=False)
        if contactpoint_node:
            if dataset_graph.value(subject=contactpoint_node, predicate=RDF.type, any=False) == VCARD.VCard:
                remove_node_from_graph(contactpoint_node, dataset_graph)

        # This is FDP specific: Dataset points back to the Catalog
        if not dataset_graph.value(subject=dataset, predicate=DCTERMS.isPartOf, any=False):
            dataset_graph.add((dataset, DCTERMS.isPartOf, catalog_uri))


def add_or_update_dataset(
    metadata: "Graph",
    fdpclient: FDPClient,
    dataset_identifier: str = None,
    catalog_uri: str = None,
    sparql: FDPSPARQLClient = None,
):
    """Either posts or updates a dataset on a FAIR Data Point

    For updating, you will need to provide a dataset identfier, URI of the parent catalog and an
    instance of an FDP-SPARQL client. If any of these are missing, datasets will always be created
    instead of being updated.

    Parameters
    ----------
    metadata : Graph
        The metadata to be published
    fdpclient : FDPClient
        Instance of FDPClient where the dataset will be pushed to
    dataset_identifier : str, optional
        DCAT Identifier of the dataset to match for updating the dataset, by default None
    catalog_uri : str, optional
        URI of the parent catalog to post data to, by default None
    sparql : FDPSPARQLClient, optional
        Instance of FDPSPARQLClient which will be queried for the dataset IRI, by default None
    """
    if sparql and dataset_identifier and catalog_uri:
        if fdp_subject_uri := sparql.find_subject(dataset_identifier, catalog_uri):
            logger.debug("Matched subject to %s", fdp_subject_uri)
            old_subject = metadata.value(predicate=RDF.type, object=DCAT.Dataset, any=False)
            rewrite_graph_subject(metadata, old_subject, fdp_subject_uri)
            return fdpclient.update_serialized(fdp_subject_uri, metadata)
        else:
            logger.debug("No match found")
    else:
        logger.debug("Not all information for potential updating is given, create and publishing.")

    return fdpclient.create_and_publish("dataset", metadata)


def rewrite_graph_subject(g: Graph, oldsubject: Union[str, URIRef], newsubject: Union[str, URIRef]):
    """Modifies a graph such that all elements of the oldsubject are replaced by newsubject

    Needed by the FDP update functionality to work around some ill-defined behavior

    Parameters
    ----------
    g : Graph
        Reference graph in which the subject will be replaced, in-place
    oldsubject : str, URIRef
        The old subject which is to be replaced
    newsubject : str, URIRef
        New subject which will replace the old subject
    """
    for s, p, o in g.triples((URIRef(oldsubject), None, None)):
        g.add((URIRef(newsubject), p, o))
        g.remove((s, p, o))
