import logging
from pathlib import Path
from typing import Dict, List, Union

from rdflib import Graph, DCAT, DCTERMS, FOAF
from sempyro.vcard import VCARD

logger = logging.getLogger(__name__)

class RDFOutput:
    """ Output class that handles writing to RDF files

    Parameters
    ----------
    config : Dict
        Dictionary containing the contents of the configuration
    format : str
        Format to serialize to.

    """
    def __init__(self, config: Dict, format: str = "turtle") -> None:
        self.config = config
        self.format = format

    def create_graph(self, input_obj: Dict[str, List[Dict]]) -> None:
        """ Create graph from Health-RI concept objects

        Parameters
        ----------
        input_obj: Dict[str, List[Dict]]
            Dictionary with a list of Health-RI concept objects per concept type

        """
        self.graph = Graph()
        # To make output cleaner, bind these prefixes to namespaces
        self.graph.bind("dcat", DCAT)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("vcard", VCARD)
        for concept_obj in input_obj.values():
            for obj in concept_obj:
                self.graph += obj['model_object'].to_graph(obj['uri'])
        logger.debug("Finished acquiring RDF graph")

    def to_stdout(self, input_obj: Dict[str, List[Dict]]) -> None:
        """ Create Health-RI concept objects to stdout

        Parameters
        ----------
        input_obj: Dict[str, List[Dict]]
            Dictionary with a list of Health-RI concept objects per concept type

        """
        self.create_graph(input_obj)
        logger.debug("Sending output to stdout")
        print(self.graph.serialize(format=self.format))

    def to_file(self, input_obj: Dict[str, List[Dict]], output_path: Union[str, Path]) -> None:
        """ Create Health-RI concept objects to file

        Parameters
        ----------
        input_obj: Dict[str, List[Dict]]
            Dictionary with a list of Health-RI concept objects per concept type
        output_path: Union[str, Path]
            Path to write the output file to

        """
        self.create_graph(input_obj)
        logger.debug("Output option set, serializing output to file %s in %s format",
                     output_path, self.format)
        self.graph.serialize(destination=output_path, format=self.format)
