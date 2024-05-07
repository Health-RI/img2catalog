import pathlib
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from sempyro.dcat.dcat_catalog import DCATCatalog
from sempyro.dcat.dcat_dataset import DCATDataset

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import xnat
from rdflib import DCAT, DCTERMS, Graph, URIRef
from rdflib.compare import to_isomorphic

from img2catalog.xnat_parser import (
    VCARD,
    XNATParserError,
    _check_elligibility_project,
    xnat_list_datasets,
    xnat_to_DCATDataset,
    xnat_to_RDF,
)

TEST_CONFIG = pathlib.Path(__file__).parent / "example-config.toml"


# Taken from cedar2fdp
@pytest.fixture()
def empty_graph():
    graph = Graph()
    graph.bind("dcat", DCAT)
    graph.bind("dcterms", DCTERMS)
    graph.bind("v", VCARD)
    return graph


@pytest.fixture()
def config():
    """Loads the default configuration TOML"""
    config_path = TEST_CONFIG

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    return config


@pytest.fixture()
def mock_catalog():
    catalog = DCATCatalog(title=["Example XNAT catalog"], description=["This is an example XNAT catalog description"])
    return catalog


@pytest.fixture()
def mock_dataset():
    dataset = DCATDataset(title=["test project"], description=["test description"])
    return dataset


@patch("xnat.session.BaseXNATSession")
def test_empty_xnat(session, empty_graph: Graph, config: Dict[str, Any]):
    """Test case for an XNAT with no projects at all"""
    # XNATSession is a key-value store so pretend it is a Dict
    session.projects = {}
    session.url_for.return_value = "https://example.com"

    empty_graph = empty_graph.parse(source="tests/references/empty_xnat.ttl")

    expected = xnat_to_RDF(session, config)

    # Compare to reference graph
    assert to_isomorphic(expected) == to_isomorphic(empty_graph)


@patch("xnat.core.XNATBaseObject")
def test_valid_project(project, empty_graph: Graph, config: Dict[str, Any]):
    """Test if a valid project generates valid output"""
    project.name = "Basic test project to test the img2catalog"
    project.description = "In this project, we test xnat and dcat and make sure a description appears."
    project.external_uri.return_value = "http://localhost/data/archive/projects/test_img2catalog"
    project.keywords = "test demo dcat"
    project.pi.firstname = "Albus"
    project.pi.lastname = "Dumbledore"
    project.pi.title = "prof."

    empty_graph = empty_graph.parse(source="tests/references/valid_project.ttl")
    dcat, uri = xnat_to_DCATDataset(project, config)
    gen = dcat.to_graph(uri)

    assert to_isomorphic(empty_graph) == to_isomorphic(gen)


@patch("xnat.core.XNATBaseObject")
def test_empty_description(project, config: Dict[str, Any]):
    """Test if a valid project generates valid output"""
    project.name = "Basic test project to test the img2catalog"
    project.description = None
    project.external_uri.return_value = "http://localhost/data/archive/projects/test_img2catalog"
    project.keywords = "test demo dcat"
    project.pi.firstname = "Albus"
    project.pi.lastname = "Dumbledore"
    project.pi.title = "prof."

    with pytest.raises(ValueError):
        xnat_to_DCATDataset(project, config).to_graph(userinfo_format=VCARD.VCard)


@patch("xnat.core.XNATBaseObject")
def test_invalid_PI(project, config: Dict[str, Any]):
    """Make sure if PI field is invalid, an exception is raised"""
    project.name = "Basic test project to test the img2catalog"
    project.description = "In this project, we test xnat and dcat and make sure a description appears."
    project.external_uri.return_value = "http://localhost/data/archive/projects/test_img2catalog"
    project.keywords = "test demo dcat"
    project.pi.firstname = None
    project.pi.lastname = None

    with pytest.raises(ValueError):
        xnat_to_DCATDataset(project, config)


@patch("xnat.core.XNATBaseObject")
def test_no_keywords(project, empty_graph: Graph, config: Dict[str, Any]):
    """Valid project without keywords, make sure it is not defined in output"""
    project.name = "Basic test project to test the img2catalog"
    project.description = "In this project, we test xnat and dcat and make sure a description appears."
    project.external_uri.return_value = "http://localhost/data/archive/projects/test_img2catalog"
    project.keywords = ""
    project.pi.firstname = "Albus"
    project.pi.lastname = "Dumbledore"
    project.pi.title = "prof."

    empty_graph = empty_graph.parse(source="tests/references/no_keyword.ttl")
    dcat, uri = xnat_to_DCATDataset(project, config)
    gen = dcat.to_graph(uri)

    assert to_isomorphic(empty_graph) == to_isomorphic(gen)


@pytest.mark.parametrize(
    "private, optin, expected", [(False, True, True), (True, True, False), (False, False, False), (True, False, False)]
)
@patch("xnat.core.XNATBaseObject")
@patch("img2catalog.xnat_parser._check_optin_optout")
@patch("img2catalog.xnat_parser.xnat_private_project")
def test_project_elligiblity(xnat_private_project, _check_optin_optout, project, private, optin, expected):
    project.__str__.return_value = "test project"
    project.id = "test"
    xnat_private_project.return_value = private
    _check_optin_optout.return_value = optin

    assert _check_elligibility_project(project, None) == expected
    # pass


@patch("img2catalog.xnat_parser._check_elligibility_project")
@patch("img2catalog.xnat_parser.xnat_to_DCATDataset")
def test_xnat_lister(xnat_to_DCATDataset, _check_elligibility_project):
    class SimpleProject:
        def __init__(self, project_id):
            self.id = None
            self.name = project_id

    # xnat_list_datasets
    session = MagicMock(spec=xnat.session.XNATSession)
    session.projects.values.return_value = [
        SimpleProject("p1"),
        SimpleProject("p2"),
        SimpleProject("p3"),
        SimpleProject("p4"),
    ]

    _check_elligibility_project.side_effect = [True, False, True, True]
    xnat_to_DCATDataset.side_effect = [
        ("project_1", "uri1"),
        ("project_3", "uri2"),
        XNATParserError("Test error", ["This project cannot be converted"]),
    ]

    list_result = xnat_list_datasets(session, {})

    assert list_result == [("project_1", "uri1"), ("project_3", "uri2")]

    assert _check_elligibility_project.call_count == 4
    assert xnat_to_DCATDataset.call_count == 3


@patch("xnat.session.BaseXNATSession")
@patch("img2catalog.xnat_parser.xnat_to_DCATCatalog")
@patch("img2catalog.xnat_parser.xnat_list_datasets")
def test_xnat_to_rdf(xnat_list_datasets, xnat_to_DCATCatalog, session, mock_dataset, mock_catalog, config, empty_graph):
    xnat_to_DCATCatalog.return_value = mock_catalog

    session.projects = {}
    session.url_for.return_value = "https://example.com"

    xnat_list_datasets.return_value = [(mock_dataset, URIRef("https://example.com/dataset"))]

    result_graph = xnat_to_RDF(session, config)
    reference_graph = empty_graph.parse(source="tests/references/minimal_catalog_dataset.ttl")

    assert to_isomorphic(result_graph) == to_isomorphic(reference_graph)
