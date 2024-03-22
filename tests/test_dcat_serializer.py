import pathlib
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import xnat
from rdflib import DCAT, DCTERMS, Graph
from rdflib.compare import to_isomorphic

from img2catalog.xnat_parser import (
    VCARD,
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


@patch("xnat.session.BaseXNATSession")
def test_empty_xnat(session, empty_graph: Graph, config: Dict[str, Any]):
    """Test case for an XNAT with no projects at all"""
    # XNATSession is a key-value store so pretend it is a Dict
    session.projects = {}
    session.url_for.return_value = "https://xnat.bmia.nl"

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
    gen = xnat_to_DCATDataset(project, config).to_graph(userinfo_format=VCARD.VCard)

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
    gen = xnat_to_DCATDataset(project, config).to_graph(userinfo_format=VCARD.VCard)

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
        def __init__(self, id):
            self.id = None

    # xnat_list_datasets
    session = MagicMock(spec=xnat.session.XNATSession)
    session.projects.values.return_value = [SimpleProject("p1"), SimpleProject("p2"), SimpleProject("p3")]

    _check_elligibility_project.side_effect = [True, False, True]
    xnat_to_DCATDataset.side_effect = ["project_1", "project_3", RuntimeError("Only two projects should be converted")]

    list_result = xnat_list_datasets(session, {})

    assert list_result == ["project_1", "project_3"]

    assert _check_elligibility_project.call_count == 3
    assert xnat_to_DCATDataset.call_count == 2
