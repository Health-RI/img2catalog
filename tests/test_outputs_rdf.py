from rdflib import URIRef
from rdflib.compare import to_isomorphic

from img2catalog.outputs.rdf import RDFOutput


def test_xnat_to_rdf(mock_dataset, mock_catalog, config, empty_graph):
    """Tests if XNAT to RDF pushing happens with correct arguments and graph is modified correctly

    Tests if `xnat_to_RDF` creates a Catalog based on the XNAT URL from the XNATSession object, and combines them
    properly with the discovered datasets.
    """
    mock_catalog.dataset = [URIRef('https://example.com/dataset')]
    mapped_objects = {
        'catalog': [{
            'uri': URIRef('https://example.com'),
            'model_object': mock_catalog}],
        'dataset': [{
            'uri': URIRef('https://example.com/dataset'),
            'model_object': mock_dataset}]
    }
    rdf_output = RDFOutput(config)
    rdf_output.create_graph(mapped_objects)
    reference_graph = empty_graph.parse(source="tests/references/minimal_dcat_catalog_dataset.ttl")

    assert to_isomorphic(rdf_output.graph) == to_isomorphic(reference_graph)
