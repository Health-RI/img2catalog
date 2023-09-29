import pytest
from unittest.mock import patch

from rdflib import Graph, DCAT, DCTERMS
from rdflib.compare import to_isomorphic

from xnatdcat.xnat_parser import XNAT_to_DCAT, xnat_to_DCATDataset, VCARD


# Taken from cedar2fdp
@pytest.fixture()
def empty_graph():
    graph = Graph()
    graph.bind("dcat", DCAT)
    graph.bind("dcterms", DCTERMS)
    graph.bind("v", VCARD)
    return graph


@patch("xnat.session.BaseXNATSession")
def test_empty_xnat(session, empty_graph):
    """Test case for an XNAT with no projects at all"""
    # XNATSession is a key-value store so pretent it is a Dict
    session.projects = {}
    expected = XNAT_to_DCAT(session)
    # Compare to empty reference graph
    assert to_isomorphic(expected) == to_isomorphic(empty_graph)


@patch("xnat.core.XNATBaseObject")
def test_valid_project(project):
    """Test if a valid project generates valid output"""
    project.name = 'Basic test project to test the xnatdcat'
    project.description = 'In this project, we test xnat and dcat and make sure a description appears.'
    project.external_uri.return_value = 'http://localhost/data/archive/projects/test_xnatdcat'
    project.keywords = 'test demo dcat'
    project.pi.firstname = 'Albus'
    project.pi.lastname = 'Dumbledore'
    project.pi.title = 'prof.'

    ref = Graph()
    ref = ref.parse(source='tests/references/valid_project.ttl')
    gen = xnat_to_DCATDataset(project).to_graph(userinfo_format=VCARD.VCard)

    print(ref.serialize())
    print(gen.serialize())

    assert to_isomorphic(ref) == to_isomorphic(gen)


@patch("xnat.core.XNATBaseObject")
def test_invalid_PI(project):
    """Make sure if PI field is invalid, an exception is raised"""
    project.name = 'Basic test project to test the xnatdcat'
    project.description = 'In this project, we test xnat and dcat and make sure a description appears.'
    project.external_uri.return_value = 'http://localhost/data/archive/projects/test_xnatdcat'
    project.keywords = 'test demo dcat'
    project.pi.firstname = None
    project.pi.lastname = None

    with pytest.raises(ValueError):
        xnat_to_DCATDataset(project)


@patch("xnat.core.XNATBaseObject")
def test_no_keywords(project):
    """Valid project without keywords, make sure it is not defined in output"""
    project.name = 'Basic test project to test the xnatdcat'
    project.description = 'In this project, we test xnat and dcat and make sure a description appears.'
    project.external_uri.return_value = 'http://localhost/data/archive/projects/test_xnatdcat'
    project.keywords = ''
    project.pi.firstname = 'Albus'
    project.pi.lastname = 'Dumbledore'
    project.pi.title = 'prof.'

    ref = Graph()
    ref = ref.parse(source='tests/references/no_keyword.ttl')
    gen = xnat_to_DCATDataset(project).to_graph(userinfo_format=VCARD.VCard)

    print(ref.serialize())
    print(gen.serialize())

    assert to_isomorphic(ref) == to_isomorphic(gen)
