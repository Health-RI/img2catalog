from datetime import datetime

import pytest
from pydantic import ValidationError
from rdflib import URIRef
from rdflib.compare import to_isomorphic

from img2catalog.mappings.xnat import map_xnat_to_healthriv1


def test_valid_project(empty_graph):
    unmapped_objects = {
        'catalog': [{
            'uri': "https://example.com",
            'title': 'Example XNAT catalog',
            'description': 'This is an example XNAT catalog description',
            'publisher': {
                'identifier': 'http://www.example.com/institution#example',
                'name': ['Example publishing institution']
            },
            'dataset': ["http://localhost/data/archive/projects/test_img2catalog"],
        }],
        'dataset': [{
            "contact_point": {
                "email": "mailto:datamanager@example.com",
                "full_name": "Example Data Management office",
                "identifier": "http://example.com"
            },
            "creator": [
                {
                    'identifier': 'http://example.com',
                    'name': ['prof. Albus Dumbledore'],
                },
                {
                    'identifier': 'http://example.com',
                    'name': ['Prof. Minerva McGonagall']
                }
            ],
            "description": ['In this project, we test "xnat" & dcat and make sure a description appears.'],
            "issued": datetime(2024, 4, 1, 0, 0),
            "identifier": "http://localhost/data/archive/projects/test_img2catalog",
            "keyword": ['test', 'demo', 'dcat'],
            "license": 'http://example.com/license#nolicense',
            "modified": datetime(2024, 4, 1, 0, 0),
            "publisher": {
                'identifier': 'http://example.com',
                'name': ['Example publisher list']
            },
            'theme': 'http://publications.europa.eu/resource/authority/data-theme/HEAL',
            'title': ["Basic test project to test the img2catalog"],
            "uri": "http://localhost/data/archive/projects/test_img2catalog",
        }]
    }

    mapped_objects = map_xnat_to_healthriv1(unmapped_objects)
    assert mapped_objects['catalog'][0]['uri'] == URIRef("https://example.com")
    assert mapped_objects['dataset'][0]['uri'] == URIRef("http://localhost/data/archive/projects/test_img2catalog")

    dataset_uri = mapped_objects['dataset'][0]['uri']
    dataset_object =  mapped_objects['dataset'][0]['model_object']

    expected_dataset_graph = empty_graph.parse(source="tests/references/valid_project.ttl")
    assert to_isomorphic(dataset_object.to_graph(dataset_uri)) == to_isomorphic(expected_dataset_graph)

def test_invalid_project():
    unmapped_objects = {
        'catalog': [{
            'uri': "https://example.com",
            'title': 'Example XNAT catalog',
            'dataset': ["http://localhost/data/archive/projects/test_img2catalog"],
        }],
        'dataset': [{
            'title': ["Basic test project to test the img2catalog"],
            "uri": "http://localhost/data/archive/projects/test_img2catalog",
        }]
    }

    with pytest.raises(ValidationError):
        map_xnat_to_healthriv1(unmapped_objects)
