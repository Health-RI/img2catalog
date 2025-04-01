from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

import xnat
from freezegun import freeze_time
from rdflib import DCTERMS, Graph, URIRef
from rdflib.compare import to_isomorphic

from img2catalog.xnat_parser import (
    VCARD,
    XNATParserError,
    _check_elligibility_project,
    filter_keyword,
    xnat_list_datasets,
    xnat_to_DCATDataset,
    xnat_to_FDP,
    xnat_to_RDF,
)

import pathlib
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


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


@freeze_time("2024-04-01")
@patch("xnat.core.XNATBaseObject")
def test_valid_project_no_investigator(project, empty_graph: Graph, config: Dict[str, Any]):
    """Test if a valid project generates valid output; only PI, no other investigators"""
    project.name = "Basic test project to test the img2catalog"
    project.description = "In this project, we test xnat and dcat and make sure a description appears."
    project.external_uri.return_value = "http://localhost/data/archive/projects/test_img2catalog"
    project.keywords = "test demo dcat"
    project.pi.firstname = "Albus"
    project.pi.lastname = "Dumbledore"
    project.pi.title = "prof."
    project.investigators = False

    empty_graph = empty_graph.parse(source="tests/references/valid_project_no_investigator.ttl")
    dcat, uri = xnat_to_DCATDataset(project, config)
    gen = dcat.to_graph(uri)

    assert to_isomorphic(empty_graph) == to_isomorphic(gen)


@freeze_time("2024-04-01")
@patch("xnat.core.XNATBaseObject")
def test_valid_project(project, empty_graph: Graph, config: Dict[str, Any]):
    """Test if a valid project generates valid output; multiple investigators"""
    project.name = "Basic test project to test the img2catalog"
    project.description = "In this project, we test &quot;xnat&quot; &amp; dcat and make sure a description appears."
    project.external_uri.return_value = "http://localhost/data/archive/projects/test_img2catalog"
    project.keywords = "test demo dcat"
    project.pi.firstname = "Albus"
    project.pi.lastname = "Dumbledore"
    project.pi.title = "prof."
    # project
    project.investigators.__len__.return_value = 1
    project.investigators[0].firstname = "Minerva"
    project.investigators[0].lastname = "McGonagall"
    project.investigators[0].title = "Prof."

    empty_graph = empty_graph.parse(source="tests/references/valid_project.ttl")
    dcat, uri = xnat_to_DCATDataset(project, config)
    gen = dcat.to_graph(uri)

    assert to_isomorphic(empty_graph) == to_isomorphic(gen)


@patch("xnat.core.XNATBaseObject")
def test_empty_description(project, config: Dict[str, Any]):
    """Test that if the description is empty, an exception is raised"""
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
def test_invalid_pi(project, config: Dict[str, Any]):
    """Make sure if PI field is invalid, an exception is raised"""
    project.name = "Basic test project to test the img2catalog"
    project.description = "In this project, we test xnat and dcat and make sure a description appears."
    project.external_uri.return_value = "http://localhost/data/archive/projects/test_img2catalog"
    project.keywords = "test demo dcat"
    project.pi.firstname = None
    project.pi.lastname = None

    with pytest.raises(ValueError):
        xnat_to_DCATDataset(project, config)


@freeze_time("2024-04-01")
@patch("xnat.core.XNATBaseObject")
def test_no_keywords(project, empty_graph: Graph, config: Dict[str, Any]):
    """Valid project without keywords, make the property `keywords` it is not defined in output"""
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


@freeze_time("2024-04-01")
@patch("xnat.core.XNATBaseObject")
def test_parse_multiple_publishers(project, empty_graph: Graph):
    """Test if multiple publishers are parsed and serialized."""
    project.name = "Basic test project to test the img2catalog"
    project.description = "In this project, we test xnat and dcat and make sure a description appears."
    project.external_uri.return_value = "http://localhost/data/archive/projects/test_img2catalog"
    project.keywords = "test"
    project.pi.firstname = "Albus"
    project.pi.lastname = "Dumbledore"
    project.pi.title = "prof."
    project.investigators = False

    test_config = pathlib.Path(__file__).parent / "multi-publisher-config.toml"
    with open(test_config, "rb") as f:
        config = tomllib.load(f)

    empty_graph = empty_graph.parse(source="tests/references/multiple_publishers.ttl")
    dcat, uri = xnat_to_DCATDataset(project, config)
    gen = dcat.to_graph(uri)

    assert to_isomorphic(empty_graph) == to_isomorphic(gen)


@pytest.mark.parametrize(
    "private, optin, expected", [
        (False, True, True),
        (True, True, False),
        (False, False, False),
        (True, False, False)]
)
@patch("xnat.core.XNATBaseObject")
@patch("img2catalog.xnat_parser._check_optin_optout")
@patch("img2catalog.xnat_parser.xnat_private_project")
def test_project_elligiblity(xnat_private_project, _check_optin_optout, project, private, optin, expected):
    """ Test project elligibility; it should only be elligible if it's not private, but does have opt-in. """
    project.__str__.return_value = "test project"
    project.id = "test"
    xnat_private_project.return_value = private
    _check_optin_optout.return_value = optin

    assert _check_elligibility_project(project, None) == expected


@pytest.mark.parametrize(
    "config, expected",
    [
        ({}, ["apple", "banana", "pear"]),
        ({"img2catalog": {"optin": "banana"}}, ["apple", "pear"]),  # test default remove
        ({"img2catalog": {}}, ["apple", "banana", "pear"]),  # test no settings
        ({"img2catalog": {"optin": "banana", "remove_optin": False}}, ["apple", "banana", "pear"]),  # do not remove
        (
            {"img2catalog": {"optin": "orange", "remove_optin": True}},
            ["apple", "banana", "pear"],
        ),  # Should never happen but still
    ],
)
def test_keyword_filter(config, expected):
    keyword_list = ["apple", "banana", "pear"]
    assert sorted(filter_keyword(keyword_list, config)) == expected


@patch("img2catalog.xnat_parser._check_elligibility_project")
@patch("img2catalog.xnat_parser.xnat_to_DCATDataset")
def test_xnat_lister(xnat_to_DCATDataset, _check_elligibility_project):
    """ Test if `xnat_list_datasets` returns the right datasets based on elligibility and errors"""
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


@freeze_time("2024-04-01")
@patch("xnat.session.BaseXNATSession")
@patch("img2catalog.xnat_parser.xnat_to_DCATCatalog")
@patch("img2catalog.xnat_parser.xnat_list_datasets")
def test_xnat_to_rdf(xnat_list_datasets, xnat_to_DCATCatalog, session, mock_dataset, mock_catalog, config, empty_graph):
    """Tests if XNAT to RDF pushing happens with correct arguments and graph is modified correctly

    Tests if `xnat_to_RDF` creates a Catalog based on the XNAT URL from the XNATSession object, and combines them
    properly with the discovered datasets.
    """
    xnat_to_DCATCatalog.return_value = mock_catalog

    session.projects = {}
    session.url_for.return_value = "https://example.com"

    xnat_list_datasets.return_value = [(mock_dataset, URIRef("https://example.com/dataset"))]

    result_graph = xnat_to_RDF(session, config)
    reference_graph = empty_graph.parse(source="tests/references/minimal_dcat_catalog_dataset.ttl")

    assert to_isomorphic(result_graph) == to_isomorphic(reference_graph)


@patch("img2catalog.xnat_parser.add_or_update_dataset")
@patch("img2catalog.xnat_parser.xnat_list_datasets")
def test_xnat_to_fdp_push(xnat_list_datasets, add_or_update_dataset, mock_dataset, config, empty_graph):
    """Tests of XNAT to RDF pushing happens even when errors happen"""
    # FIXME: Figure out what the goal is of this test

    xnat_list_datasets.return_value = [(mock_dataset, URIRef("http://example.com/dataset"))]

    xnat_to_FDP(None, config, URIRef("http://example.com/catalog"), None, None)

    # Check if function is called and correct term added to Graph
    add_or_update_dataset.assert_called_once()
    assert (
        URIRef("http://example.com/dataset"),
        DCTERMS.isPartOf,
        URIRef("http://example.com/catalog"),
    ) in add_or_update_dataset.call_args.args[0], "FDP catalog reference missing"


@patch("img2catalog.xnat_parser.add_or_update_dataset")
@patch("img2catalog.xnat_parser.xnat_list_datasets")
def test_xnat_to_fdp_push_error(xnat_list_datasets, add_or_update_dataset, mock_dataset, config, empty_graph):
    # FIXME: Figure out what the goal is of this test also
    xnat_list_datasets.return_value = [
        (mock_dataset, URIRef("http://example.com/dataset1")),
        (mock_dataset, URIRef("http://example.com/dataset2")),
    ]
    add_or_update_dataset.side_effect = [ValueError, None]

    xnat_to_FDP(None, config, URIRef("http://example.com/catalog"), None, None)

    assert add_or_update_dataset.call_count == 2
    assert (
        URIRef("http://example.com/dataset2"),
        DCTERMS.isPartOf,
        URIRef("http://example.com/catalog"),
    ) in add_or_update_dataset.call_args_list[1].args[0], "FDP catalog reference missing"
