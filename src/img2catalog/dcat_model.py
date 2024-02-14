"""Pydantic models for FDP objects"""
import logging
from typing import List, Optional, Union

from pydantic.v1 import BaseModel, Field, validator
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, RDF, XSD

from .const import VCARD

logger = logging.getLogger(__name__)


class VCard(BaseModel):
    full_name: Optional[Literal] = None
    uid: Optional[URIRef] = None
    email: Optional[URIRef] = None


def add_empty_node_of_type(graph: Graph, subject, predicate, node_type=None):
    node = BNode()
    graph.add((subject, predicate, node))
    if node_type:
        graph.add((node, RDF.type, node_type))
    return node


class DCATDataSet(BaseModel):
    """DCAT Dataset model"""

    uri: URIRef
    title: List[Literal]
    description: Literal
    creator: Union[List[URIRef], List[VCard]]
    start_date: Optional[Literal] = None
    end_date: Optional[Literal] = None
    contact_point: Optional[Union[List[URIRef], List[VCard]]] = None
    publisher: Optional[Union[List[URIRef], URIRef]] = None
    keyword: Optional[List[Literal]] = Field(default_factory=list)
    theme: Optional[List[URIRef]] = Field(default_factory=list)
    is_part_of: Optional[URIRef] = None
    has_version: Optional[
        URIRef
    ] = None  # Should be dcat:version in the next version of the FDP release(aiming for 1.18.0)
    landing: Optional[URIRef] = None

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @validator("creator", "contact_point")
    def validate_empty_nodes(cls, field_value, values, field):
        """Checks if a list contains empty BNodes and removes them"""
        if any(isinstance(creator_item, BNode) for creator_item in field_value):
            logger.warning(f"One or more {field.name} instances are empty BNode objects {values['uri']}, removing")
            field_value = [item for item in field_value if not isinstance(item, BNode)]
        return field_value

    def to_graph(self, userinfo_format: str = None) -> Graph:
        """Converts class instance to DCAT dataset graph"""
        graph = Graph()
        subject = self.uri
        # For dcterms:identifier
        identifier = subject.rsplit("/", maxsplit=1)[-1]

        # First, add dataset identifier and dataset itself.
        graph.add((subject, DCTERMS.identifier, Literal(identifier, datatype=XSD.token)))
        graph.add((subject, RDF.type, DCAT.Dataset))
        for title in self.title:
            graph.add((subject, DCTERMS.title, title))

        self.add_vcard_info(
            attribute_name="creator",
            graph=graph,
            subject=subject,
            predicate=DCTERMS.creator,
            userinfo_format=userinfo_format,
        )
        if self.contact_point:
            self.add_vcard_info(
                attribute_name="contact_point",
                graph=graph,
                subject=subject,
                predicate=DCAT.contactPoint,
                userinfo_format=userinfo_format,
            )

        # This creates a blank date node, with corresponding start/end date if set
        date_node = BNode()
        graph.add((subject, DCTERMS.temporal, date_node))
        graph.add((date_node, RDF.type, DCTERMS.PeriodOfTime))
        if self.start_date:
            graph.add((date_node, DCAT.startDate, self.start_date))
        if self.end_date:
            graph.add((date_node, DCAT.endDate, self.end_date))

        if self.description:
            graph.add((subject, DCTERMS.description, self.description))
        if self.publisher is not None:
            for publisher in self.publisher:
                graph.add((subject, DCTERMS.publisher, publisher))
        if self.is_part_of:
            graph.add((subject, DCTERMS.isPartOf, self.is_part_of))
        if self.has_version:
            graph.add((subject, DCTERMS.hasVersion, self.has_version))
        if self.landing:
            graph.add((subject, DCAT.landingPage, self.landing))
        if self.keyword:
            for key_w in self.keyword:
                graph.add((subject, DCAT.keyword, key_w))
        for theme in self.theme:
            graph.add((subject, DCAT.theme, theme))

        graph.bind("dcat", DCAT)
        graph.bind("dcterms", DCTERMS)
        if userinfo_format == "vcard":
            graph.bind("v", VCARD)

        return graph

    def add_vcard_info(self, attribute_name, graph, subject, predicate, userinfo_format: URIRef = None) -> None:
        """
        Adds person information as URIRef or VCard node

        Parameters
        ----------
        attribute_name: String
            A class attribute to add to graph;
        graph: Graph
            A graph to add data
        subject: URIRef
            A subject for the node to add
        predicate: URIRef
            Target predicate
        userinfo_format: Optional, URIRef
            a format of a user record node, VCARD.VCard if "VCARD.VCard" is specified, default is not defined

        Returns
        ------
        None
        """
        attribute = getattr(self, attribute_name)

        if userinfo_format != VCARD.VCard and all(type(x) for x in attribute) == VCard:
            logger.warning(f"Items of '{attribute_name}' attribute are in VCard format")
        if attribute:
            if userinfo_format == VCARD.VCard:
                logger.debug("User info is of VCARD type")
                for item in attribute:
                    vcard_node = add_empty_node_of_type(
                        graph=graph,
                        subject=subject,
                        predicate=predicate,
                        node_type=userinfo_format,
                    )
                    graph.add((vcard_node, VCARD.fn, item.full_name))
                    if item.uid:
                        graph.add((vcard_node, VCARD.hasUID, item.uid))
                    if item.email:
                        graph.add((vcard_node, VCARD.hasEmail, item.email))

            else:
                logger.debug("User info is NOT of VCARD type")
                for item in attribute:
                    if isinstance(item, VCard):
                        item = item.uid
                    graph.add((subject, predicate, item))
        else:
            add_empty_node_of_type(
                graph=graph,
                subject=subject,
                predicate=predicate,
                node_type=userinfo_format,
            )


class DCATDistribution(BaseModel):
    """DCAT Distribution model"""

    uri: URIRef
    title: Literal
    description: Literal
    distr_format: Optional[URIRef] = None
    distr_license: Optional[URIRef] = None
    is_part_of: URIRef
    access_url: List[URIRef]

    def to_graph(self) -> Graph:
        """Converts class instance to dcat distribution graph"""
        graph = Graph()
        subject = self.uri

        graph.add((subject, RDF.type, DCAT.Distribution))
        graph.add((subject, DCTERMS.title, self.title))
        graph.add((subject, DCTERMS.description, self.description))
        if self.distr_format:
            graph.add((subject, DCTERMS.format, self.distr_format))
        graph.add((subject, DCTERMS.isPartOf, self.is_part_of))
        if self.distr_license:
            graph.add((subject, DCTERMS.license, self.distr_license))
        for access_url in self.access_url:
            graph.add((subject, DCAT.accessURL, access_url))

        graph.bind("dcat", DCAT)
        graph.bind("dcterms", DCTERMS)

        return graph


class DCATCatalog(BaseModel):
    """DCAT Catalog model"""

    uri: URIRef
    title: Literal
    description: Literal
    # publisher: FOAFAgent
    Dataset: Optional[List[URIRef]] = Field(default_factory=list)

    def to_graph(self) -> Graph:
        graph = Graph()
        graph.bind("dcat", DCAT)
        graph.bind("dcterms", DCTERMS)

        subject = self.uri
        graph.add((subject, RDF.type, DCAT.Catalog))
        graph.add((subject, DCTERMS.title, self.title))
        graph.add((subject, DCTERMS.description, self.description))

        if self.Dataset:
            for ds in self.Dataset:
                graph.add((subject, DCAT.dataset, ds))

        return graph
