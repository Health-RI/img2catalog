"""In-memory FAIR Data Point for testing the FDP output, following the reference FDP (v1.16.2).

Behaviour of the reference FDP that it follows, as checked against a running FDP:
- a created record gets a new URI, is a DRAFT until it is published, and the FDP links its parent to it
  (dcat:dataset on the Catalog, dcat:distribution on the Dataset)
- updating a record replaces its metadata, so links to its children that are not sent are removed; the FDP links its
  parent to it again
- updating keeps the state of a record, and publishing a record that is already published is refused (HTTP 400)
"""

from unittest.mock import Mock

import requests
from fairclient.sparqlclient import FDPSPARQLClient
from fairclient.utils import rewrite_graph_subject
from rdflib import DCAT, DCTERMS, RDF, Graph, URIRef

FDP_URL = "http://fdp.example.com"
FDP_ROOT = URIRef(FDP_URL)
RECORD_CLASSES = {"catalog": DCAT.Catalog, "dataset": DCAT.Dataset, "distribution": DCAT.Distribution}
PARENT_LINKS = {"dataset": DCAT.dataset, "distribution": DCAT.distribution}


class FakeFDP:
    timeout = 60

    def __init__(self):
        self.records = {}
        self.record_types = {}
        self.states = {}
        self.publish_fails = False
        self.session = self

    @property
    def datasets(self):
        return self.of_type("dataset")

    def of_type(self, record_type):
        return {uri: graph for uri, graph in self.records.items() if self.record_types[uri] == record_type}

    def _link_parent(self, uri):
        record_type = self.record_types[uri]
        parent = self.records[uri].value(uri, DCTERMS.isPartOf)
        if record_type in PARENT_LINKS and parent in self.records:
            self.records[parent].add((parent, PARENT_LINKS[record_type], uri))

    def create_and_publish(self, resource_type, metadata):
        number = len(self.of_type(resource_type)) + 1
        fdp_uri = URIRef(f"{FDP_URL}/{resource_type}/{number}")
        stored = Graph() + metadata
        old_subject = stored.value(predicate=RDF.type, object=RECORD_CLASSES[resource_type], any=False)
        rewrite_graph_subject(stored, old_subject, fdp_uri)
        self.records[fdp_uri] = stored
        self.record_types[fdp_uri] = resource_type
        self.states[fdp_uri] = "DRAFT"
        self._link_parent(fdp_uri)
        self.publish_record(fdp_uri)
        return fdp_uri

    def update_serialized(self, resource_uri, metadata):
        resource_uri = URIRef(resource_uri)
        assert resource_uri in self.records, f"Updated {resource_uri}, which does not exist in the FDP"
        self.records[resource_uri] = Graph() + metadata
        self._link_parent(resource_uri)
        return object()  # fairclient returns the requests.Response of the update

    def publish_record(self, record_url):
        if self.publish_fails:
            raise requests.ConnectionError("FDP not reachable")
        if self.states[URIRef(record_url)] == "PUBLISHED":
            raise requests.HTTPError("400 Bad Request: Metadata is already published")
        self.states[URIRef(record_url)] = "PUBLISHED"

    def get(self, url, headers, timeout):
        """requests.Session.get of the logged in fairclient session"""
        assert timeout
        if url.endswith("/meta"):
            assert headers == {"Accept": "application/json"}
            state = self.states[URIRef(url[: -len("/meta")])]
            return Mock(raise_for_status=Mock(), json=Mock(return_value={"state": {"current": state}}))
        assert headers == {"Accept": "text/turtle"}
        if URIRef(url) == FDP_ROOT:
            root = Graph()
            root.add((FDP_ROOT, RDF.type, URIRef("https://w3id.org/fdp/fdp-o#FAIRDataPoint")))
            return Mock(raise_for_status=Mock(), text=root.serialize(format="turtle"))
        if URIRef(url) not in self.records:
            raise requests.HTTPError(f"404 Not Found: {url}")
        return Mock(raise_for_status=Mock(), text=self.records[URIRef(url)].serialize(format="turtle"))

    def graph(self):
        """All metadata in the FDP, like its triple store."""
        store = Graph()
        for graph in self.records.values():
            store += graph
        return store


class FakeSPARQLEndpoint:
    """SPARQL endpoint of the FakeFDP, which runs the actual SPARQL queries on its records."""

    def __init__(self, fdp):
        self.fdp = fdp
        self.queries = []

    def setQuery(self, query):  # noqa: N802 - SPARQLWrapper API
        self.queries.append(query)

    def queryAndConvert(self):  # noqa: N802 - SPARQLWrapper API
        rows = self.fdp.graph().query(self.queries[-1])
        return {"results": {"bindings": [{"subject": {"type": "uri", "value": str(row.subject)}} for row in rows]}}


def connect_fake_fdp(fdp_output, sparql=True):
    """Make an FDPOutput push to a new FakeFDP, and return the FakeFDP."""
    fdp = FakeFDP()
    fdp_output.fdp = FDP_URL
    fdp_output.fdpclient = fdp
    fdp_output.sparqlclient = None
    if sparql:
        fdp_output.sparqlclient = FDPSPARQLClient(f"{FDP_URL}/sparql")
        fdp_output.sparqlclient.sparql = FakeSPARQLEndpoint(fdp)
    return fdp
