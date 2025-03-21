import logging

from rdflib import Graph, DCAT, DCTERMS, FOAF
from sempyro.vcard import VCARD

logger = logging.getLogger(__name__)

class RDFOutput:
    def __init__(self, config, format):
        self.config = config
        self.format = format

    def create_graph(self, input_obj):
        self.graph = Graph()
        # To make output cleaner, bind these prefixes to namespaces
        self.graph.bind("dcat", DCAT)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("vcard", VCARD)
        for _, concept_obj in input_obj.items():
            for obj in concept_obj:
                self.graph += obj['model_object'].to_graph(obj['uri'])
        logger.debug("Finished acquiring RDF graph")

    def to_stdout(self, input_obj):
        self.create_graph(input_obj)
        logger.debug("Sending output to stdout")
        print(self.graph.serialize(format=self.format))

    def to_file(self, input_obj, output_path):
        self.create_graph(input_obj)
        logger.debug("Output option set, serializing output to file %s in %s format",
                     output_path, self.format)
        self.graph.serialize(destination=output_path, format=self.format)
