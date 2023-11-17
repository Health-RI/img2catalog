from pathlib import Path
from typing import Any, Dict
import pytest
from unittest.mock import patch

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from rdflib import Graph, DCAT, DCTERMS
from rdflib.compare import to_isomorphic

from xnatdcat.xnat_parser import xnat_to_RDF, xnat_to_DCATDataset, VCARD
from xnatdcat.const import EXAMPLE_CONFIG_PATH


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
    config_path = EXAMPLE_CONFIG_PATH

    with open(config_path, 'rb') as f:
        config = tomllib.load(f)

    return config


@patch("xnat.session.BaseXNATSession")
def test_empty_xnat(session, empty_graph: Graph, config: Dict[str, Any]):
    """Test case for an XNAT with no projects at all"""
    # XNATSession is a key-value store so pretent it is a Dict
    session.projects = {}
    session.url_for.return_value = 'https://xnat.bmia.nl'

    empty_graph = empty_graph.parse(source='tests/references/empty_xnat.ttl')

    expected = xnat_to_RDF(session, config)

    # Compare to reference graph
    assert to_isomorphic(expected) == to_isomorphic(empty_graph)


@patch("xnat.core.XNATBaseObject")
def test_valid_project(project, empty_graph: Graph, config: Dict[str, Any]):
    """Test if a valid project generates valid output"""
    project.name = 'Basic test project to test the xnatdcat'
    project.description = 'In this project, we test xnat and dcat and make sure a description appears.'
    project.external_uri.return_value = 'http://localhost/data/archive/projects/test_xnatdcat'
    project.keywords = 'test demo dcat'
    project.pi.firstname = 'Albus'
    project.pi.lastname = 'Dumbledore'
    project.pi.title = 'prof.'

    empty_graph = empty_graph.parse(source='tests/references/valid_project.ttl')
    gen = xnat_to_DCATDataset(project, config).to_graph(userinfo_format=VCARD.VCard)

    assert to_isomorphic(empty_graph) == to_isomorphic(gen)


@patch("xnat.core.XNATBaseObject")
def test_empty_description(project, config: Dict[str, Any]):
    """Test if a valid project generates valid output"""
    project.name = 'Basic test project to test the xnatdcat'
    project.description = None
    project.external_uri.return_value = 'http://localhost/data/archive/projects/test_xnatdcat'
    project.keywords = 'test demo dcat'
    project.pi.firstname = 'Albus'
    project.pi.lastname = 'Dumbledore'
    project.pi.title = 'prof.'

    with pytest.raises(ValueError):
        xnat_to_DCATDataset(project, config).to_graph(userinfo_format=VCARD.VCard)


@patch("xnat.core.XNATBaseObject")
def test_invalid_PI(project, config: Dict[str, Any]):
    """Make sure if PI field is invalid, an exception is raised"""
    project.name = 'Basic test project to test the xnatdcat'
    project.description = 'In this project, we test xnat and dcat and make sure a description appears.'
    project.external_uri.return_value = 'http://localhost/data/archive/projects/test_xnatdcat'
    project.keywords = 'test demo dcat'
    project.pi.firstname = None
    project.pi.lastname = None

    with pytest.raises(ValueError):
        xnat_to_DCATDataset(project, config)


@patch("xnat.core.XNATBaseObject")
def test_no_keywords(project, empty_graph: Graph, config: Dict[str, Any]):
    """Valid project without keywords, make sure it is not defined in output"""
    project.name = 'Basic test project to test the xnatdcat'
    project.description = 'In this project, we test xnat and dcat and make sure a description appears.'
    project.external_uri.return_value = 'http://localhost/data/archive/projects/test_xnatdcat'
    project.keywords = ''
    project.pi.firstname = 'Albus'
    project.pi.lastname = 'Dumbledore'
    project.pi.title = 'prof.'

    empty_graph = empty_graph.parse(source='tests/references/no_keyword.ttl')
    gen = xnat_to_DCATDataset(project, config).to_graph(userinfo_format=VCARD.VCard)

    assert to_isomorphic(empty_graph) == to_isomorphic(gen)
