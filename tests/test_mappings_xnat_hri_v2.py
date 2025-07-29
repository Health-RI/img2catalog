from datetime import datetime

import pytest
from pydantic import ValidationError
from rdflib import URIRef
from rdflib.compare import to_isomorphic
from sempyro import LiteralField

from img2catalog.mappings.xnat import map_xnat_to_healthriv2


def test_valid_project(empty_graph):
    unmapped_objects = {
        'catalog': [{
            'uri': "https://example.com",
            'title': 'Example XNAT catalog',
            'description': 'This is an example XNAT catalog description',
            'publisher': {
                'identifier': ['http://www.example.com/institution#example'],
                'name': ['Example publishing institution'],
                'mbox': "example@example.com",
                'homepage': 'http://www.example.com'
            },
            'contact_point': {
                'email': 'mailto:example@example.com',
                'formatted_name': 'Servicedesk at Example Institution'
            },
            'dataset': ["http://localhost/data/archive/projects/test_img2catalog"],
        }],
        'dataset': [{
            "contact_point": {
                "email": "mailto:datamanager@example.com",
                "formatted_name": "Example Data Management office",
                "identifier": "http://example.com"
            },
            "creator": [
                {
                    'identifier': ['http://example.com', "http://anotherone.example.com"],
                    'name': ['prof. Albus Dumbledore', "Hogwarts' Headmaster"],
                    'mbox': "mailto:example@example.com",
                    'homepage': 'http://www.example.com'
                },
                {
                    'identifier': ['http://example.com'],
                    'name': ['Prof. Minerva McGonagall'],
                    'mbox': "mailto:example@example.com",
                    'homepage': 'http://www.example.com'
                }
            ],
            "description": ['In this project, we test "xnat" & dcat and make sure a description appears.'],
            "issued": datetime(2024, 4, 1, 0, 0),
            "identifier": "http://localhost/data/archive/projects/test_img2catalog",
            "keyword": ['test', 'demo', 'dcat'],
            "modified": datetime(2024, 4, 1, 0, 0),
            "publisher": {
                'identifier': ['http://example.com'],
                'name': ['Example publisher list'],
                'mbox': "mailto:example@example.com",
                'homepage': 'http://www.example.com'
            },
            'theme': 'http://publications.europa.eu/resource/authority/data-theme/HEAL',
            'title': ["Basic test project to test the img2catalog"],
            "uri": "http://localhost/data/archive/projects/test_img2catalog",
            "access_rights": "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC",
            "applicable_legislation": ["http://data.europa.eu/eli/reg/2025/327/oj"]
        }]
    }

    mapped_objects = map_xnat_to_healthriv2(unmapped_objects)
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
        map_xnat_to_healthriv2(unmapped_objects)


def test_invalid_project_no_keywords(empty_graph):
    unmapped_objects = {
        'catalog': [{
            'uri': "https://example.com",
            'title': 'Example XNAT catalog',
            'description': 'This is an example XNAT catalog description',
            'publisher': {
                'identifier': ['http://www.example.com/institution#example'],
                'name': ['Example publishing institution'],
                'mbox': "example@example.com",
                'homepage': 'http://www.example.com'
            },
            'contact_point': {
                'email': 'mailto:example@example.com',
                'formatted_name': 'Servicedesk at Example Institution'
            },
            'dataset': ["http://localhost/data/archive/projects/test_img2catalog"],
        }],
        'dataset': [{
            "contact_point": {
                "email": "mailto:datamanager@example.com",
                "formatted_name": "Example Data Management office",
                "identifier": "http://example.com"
            },
            "creator": [
                {
                    'identifier': ['http://example.com', "http://anotherone.example.com"],
                    'name': ['prof. Albus Dumbledore', "Hogwarts' Headmaster"],
                    'mbox': "mailto:example@example.com",
                    'homepage': 'http://www.example.com'
                },
                {
                    'identifier': ['http://example.com'],
                    'name': ['Prof. Minerva McGonagall'],
                    'mbox': "mailto:example@example.com",
                    'homepage': 'http://www.example.com'
                }
            ],
            "description": ['In this project, we test "xnat" & dcat and make sure a description appears.'],
            "issued": datetime(2024, 4, 1, 0, 0),
            "identifier": "http://localhost/data/archive/projects/test_img2catalog",
            # "keyword": ['test', 'demo', 'dcat'],
            "modified": datetime(2024, 4, 1, 0, 0),
            "publisher": {
                'identifier': ['http://example.com'],
                'name': ['Example publisher list'],
                'mbox': "mailto:example@example.com",
                'homepage': 'http://www.example.com'
            },
            'theme': 'http://publications.europa.eu/resource/authority/data-theme/HEAL',
            'title': ["Basic test project to test the img2catalog"],
            "uri": "http://localhost/data/archive/projects/test_img2catalog",
            "access_rights": "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC",
            "applicable_legislation": ["http://data.europa.eu/eli/reg/2025/327/oj"]
        }]
    }

    with pytest.raises(ValidationError):
        map_xnat_to_healthriv2(unmapped_objects)


def test_catalog_publisher_as_list():
    """Test catalog with publisher as list"""
    unmapped_objects = {
        'catalog': [{
            'uri': "https://example.com",
            'title': 'Example XNAT catalog',
            'description': 'This is an example XNAT catalog description',
            'publisher': [  # Publisher as list - should be converted to single item
                {
                    'identifier': ['http://www.example.com/institution#example'],
                    'name': ['Example publishing institution'],
                    'mbox': "example@example.com",
                    'homepage': 'http://www.example.com'
                }
            ],
            'contact_point': {
                'email': 'mailto:example@example.com',
                'formatted_name': 'Servicedesk at Example Institution'
            },
            'dataset': ["http://localhost/data/archive/projects/test_img2catalog"],
        }],
        'dataset': [{
            "contact_point": {
                "email": "mailto:datamanager@example.com",
                "formatted_name": "Example Data Management office",
            },
            "creator": [{
                'identifier': ['http://example.com'],
                'name': ['prof. Albus Dumbledore'],
                'mbox': "mailto:example@example.com",
                'homepage': 'http://www.example.com'
            }],
            "description": ['Test description'],
            "issued": datetime(2024, 4, 1, 0, 0),
            "identifier": "http://localhost/data/archive/projects/test_img2catalog",
            "keyword": ['test'],
            "modified": datetime(2024, 4, 1, 0, 0),
            'title': ["Test project"],
            "uri": "http://localhost/data/archive/projects/test_img2catalog",
            "access_rights": "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC",
            "applicable_legislation": ["http://data.europa.eu/eli/reg/2025/327/oj"],
            'publisher': {
                'identifier': ['http://www.example.com/institution#example'],
                'name': ['Example publishing institution'],
                'mbox': "example@example.com",
                'homepage': 'http://www.example.com'
            },
            'theme': 'http://publications.europa.eu/resource/authority/data-theme/HEAL'
        }]
    }

    mapped_objects = map_xnat_to_healthriv2(unmapped_objects)
    
    # Should successfully map with publisher converted from list
    assert mapped_objects['catalog'][0]['uri'] == URIRef("https://example.com")
    assert mapped_objects['catalog'][0]['model_object'].publisher is not None
    assert mapped_objects['catalog'][0]['model_object'].publisher.name == ['Example publishing institution']


def test_dataset_publisher_as_list():
    """Test dataset with publisher as list"""
    unmapped_objects = {
        'catalog': [{
            'uri': "https://example.com",
            'title': 'Example XNAT catalog',
            'description': 'This is an example XNAT catalog description',
            'publisher': {
                'identifier': ['http://www.example.com/institution#example'],
                'name': ['Example publishing institution'],
                'mbox': "example@example.com",
                'homepage': 'http://www.example.com'
            },
            'contact_point': {
                'email': 'mailto:example@example.com',
                'formatted_name': 'Servicedesk at Example Institution'
            },
            'dataset': ["http://localhost/data/archive/projects/test_img2catalog"],
        }],
        'dataset': [{
            "contact_point": {
                "email": "mailto:datamanager@example.com",
                "formatted_name": "Example Data Management office",
            },
            "creator": [{
                'identifier': ['http://example.com'],
                'name': ['prof. Albus Dumbledore'],
                'mbox': "mailto:example@example.com",
                'homepage': 'http://www.example.com'
            }],
            "description": ['Test description'],
            "issued": datetime(2024, 4, 1, 0, 0),
            "identifier": "http://localhost/data/archive/projects/test_img2catalog",
            "keyword": ['test'],
            "modified": datetime(2024, 4, 1, 0, 0),
            "publisher": [  # Publisher as list - should be converted to single item
                {
                    'identifier': ['http://example.com'],
                    'name': ['Example dataset publisher'],
                    'mbox': "mailto:publisher@example.com",
                    'homepage': 'http://www.example.com'
                }
            ],
            'title': ["Test project"],
            "uri": "http://localhost/data/archive/projects/test_img2catalog",
            "access_rights": "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC",
            "applicable_legislation": ["http://data.europa.eu/eli/reg/2025/327/oj"],
            'theme': 'http://publications.europa.eu/resource/authority/data-theme/HEAL'
        }]
    }

    mapped_objects = map_xnat_to_healthriv2(unmapped_objects)
    
    # Should successfully map with dataset publisher converted from list
    assert mapped_objects['dataset'][0]['uri'] == URIRef("http://localhost/data/archive/projects/test_img2catalog")
    assert mapped_objects['dataset'][0]['model_object'].publisher is not None
    assert mapped_objects['dataset'][0]['model_object'].publisher.name == ['Example dataset publisher']


def test_dataset_theme_as_single_string():
    """Test dataset with theme as single string"""
    unmapped_objects = {
        'catalog': [{
            'uri': "https://example.com",
            'title': 'Example XNAT catalog',
            'description': 'This is an example XNAT catalog description',
            'publisher': {
                'identifier': ['http://www.example.com/institution#example'],
                'name': ['Example publishing institution'],
                'mbox': "example@example.com",
                'homepage': 'http://www.example.com'
            },
            'contact_point': {
                'email': 'mailto:example@example.com',
                'formatted_name': 'Servicedesk at Example Institution'
            },
            'dataset': ["http://localhost/data/archive/projects/test_img2catalog"],
        }],
        'dataset': [{
            "contact_point": {
                "email": "mailto:datamanager@example.com",
                "formatted_name": "Example Data Management office",
            },
            "creator": [{
                'identifier': ['http://example.com'],
                'name': ['prof. Albus Dumbledore'],
                'mbox': "mailto:example@example.com",
                'homepage': 'http://www.example.com'
            }],
            'publisher': {
                'identifier': ['http://www.example.com/institution#example'],
                'name': ['Example publishing institution'],
                'mbox': "example@example.com",
                'homepage': 'http://www.example.com'
            },
            "description": ['Test description'],
            "issued": datetime(2024, 4, 1, 0, 0),
            "identifier": "http://localhost/data/archive/projects/test_img2catalog",
            "keyword": ['test'],
            "modified": datetime(2024, 4, 1, 0, 0),
            'theme': 'http://publications.europa.eu/resource/authority/data-theme/HEAL',  # Single string
            'title': ["Test project"],
            "uri": "http://localhost/data/archive/projects/test_img2catalog",
            "access_rights": "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC",
            "applicable_legislation": ["http://data.europa.eu/eli/reg/2025/327/oj"]
        }]
    }

    mapped_objects = map_xnat_to_healthriv2(unmapped_objects)
    
    # Should successfully map with theme converted from string to list
    assert mapped_objects['dataset'][0]['uri'] == URIRef("http://localhost/data/archive/projects/test_img2catalog")
    assert mapped_objects['dataset'][0]['model_object'].theme == [URIRef('http://publications.europa.eu/resource/authority/data-theme/HEAL')]


def test_dataset_theme_as_list():
    """Test dataset with theme already as list (no conversion needed)"""
    unmapped_objects = {
        'catalog': [{
            'uri': "https://example.com",
            'title': 'Example XNAT catalog',
            'description': 'This is an example XNAT catalog description',
            'publisher': {
                'identifier': ['http://www.example.com/institution#example'],
                'name': ['Example publishing institution'],
                'mbox': "example@example.com",
                'homepage': 'http://www.example.com'
            },
            'contact_point': {
                'email': 'mailto:example@example.com',
                'formatted_name': 'Servicedesk at Example Institution'
            },
            'dataset': ["http://localhost/data/archive/projects/test_img2catalog"],
        }],
        'dataset': [{
            "contact_point": {
                "email": "mailto:datamanager@example.com",
                "formatted_name": "Example Data Management office",
            },
            "creator": [{
                'identifier': ['http://example.com'],
                'name': ['prof. Albus Dumbledore'],
                'mbox': "mailto:example@example.com",
                'homepage': 'http://www.example.com'
            }],
            'publisher': {
                'identifier': ['http://www.example.com/institution#example'],
                'name': ['Example publishing institution'],
                'mbox': "example@example.com",
                'homepage': 'http://www.example.com'
            },
            "description": ['Test description'],
            "issued": datetime(2024, 4, 1, 0, 0),
            "identifier": "http://localhost/data/archive/projects/test_img2catalog",
            "keyword": ['test'],
            "modified": datetime(2024, 4, 1, 0, 0),
            'theme': [  # Already a list
                'http://publications.europa.eu/resource/authority/data-theme/HEAL',
                'http://publications.europa.eu/resource/authority/data-theme/TECH'
            ],
            'title': ["Test project"],
            "uri": "http://localhost/data/archive/projects/test_img2catalog",
            "access_rights": "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC",
            "applicable_legislation": ["http://data.europa.eu/eli/reg/2025/327/oj"]
        }]
    }

    mapped_objects = map_xnat_to_healthriv2(unmapped_objects)
    
    # Should successfully map with theme list preserved
    assert mapped_objects['dataset'][0]['uri'] == URIRef("http://localhost/data/archive/projects/test_img2catalog")
    expected_themes = [
        URIRef('http://publications.europa.eu/resource/authority/data-theme/HEAL'),
        URIRef('http://publications.europa.eu/resource/authority/data-theme/TECH')
    ]
    assert mapped_objects['dataset'][0]['model_object'].theme == expected_themes


# Base dataset template for parametrized tests
BASE_DATASET_TEMPLATE = {
    "contact_point": {
        "email": "mailto:datamanager@example.com",
        "formatted_name": "Example Data Management office",
    },
    "creator": [{
        'identifier': ['http://example.com'],
        'name': ['prof. Albus Dumbledore'],
        'mbox': "mailto:example@example.com",
        'homepage': 'http://www.example.com'
    }],
    'publisher': {
        'identifier': ['http://www.example.com/institution#example'],
        'name': ['Example publishing institution'],
        'mbox': "example@example.com",
        'homepage': 'http://www.example.com'
    },
    "description": ['Test description'],
    "issued": datetime(2024, 4, 1, 0, 0),
    "identifier": "http://localhost/data/archive/projects/test_img2catalog",
    "keyword": ['test'],
    "modified": datetime(2024, 4, 1, 0, 0),
    'title': ["Test project"],
    "uri": "http://localhost/data/archive/projects/test_img2catalog",
    "access_rights": "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC",
    "applicable_legislation": ["http://data.europa.eu/eli/reg/2025/327/oj"],
    'theme': 'http://publications.europa.eu/resource/authority/data-theme/HEAL'
}

BASE_CATALOG_TEMPLATE = {
    'uri': "https://example.com",
    'title': 'Example XNAT catalog',
    'description': 'This is an example XNAT catalog description',
    'publisher': {
        'identifier': ['http://www.example.com/institution#example'],
        'name': ['Example publishing institution'],
        'mbox': "example@example.com",
        'homepage': 'http://www.example.com'
    },
    'contact_point': {
        'email': 'mailto:example@example.com',
        'formatted_name': 'Servicedesk at Example Institution'
    },
    'dataset': ["http://localhost/data/archive/projects/test_img2catalog"],
}


@pytest.mark.parametrize("field_name,field_value", [
    # URI list fields
    ("health_theme", ["http://example.com/health1", "http://example.com/health2"]),
    ("personal_data", ["http://example.com/pd1", "http://example.com/pd2"]),
    ("purpose", ["http://example.com/purpose1", "http://example.com/purpose2"]),
    ("legal_basis", ["http://example.com/legal1", "http://example.com/legal2"]),
    ("analytics", ["http://example.com/analytics1", "http://example.com/analytics2"]),
    ("code_values", ["http://example.com/code1", "http://example.com/code2"]),
    ("coding_system", ["http://example.com/coding1", "http://example.com/coding2"]),
    ("conforms_to", ["http://example.com/conforms1", "http://example.com/conforms2"]),
    ("documentation", ["http://example.com/doc1", "http://example.com/doc2"]),
    ("in_series", ["http://example.com/series1", "http://example.com/series2"]),
    ("is_referenced_by", ["http://example.com/ref1", "http://example.com/ref2"]),
    ("sample", ["http://example.com/sample1", "http://example.com/sample2"]),
    ("source", ["http://example.com/source1", "http://example.com/source2"]),
    ("type", ["http://example.com/type1", "http://example.com/type2"]),
    ("distribution", ["http://example.com/dist1", "http://example.com/dist2"]),
    # Single URI fields
    ("frequency", "http://example.com/frequency"),
    ("status", 'http://publications.europa.eu/resource/authority/dataset-status/COMPLETED'),
    ("license", "http://example.com/license"),
    # Simple fields (no URI conversion)
    ("maximum_typical_age", 100),
    ("minimum_typical_age", 0),
    ("number_of_records", 5000),
    ("number_of_unique_individuals", 1000),
    ("population_coverage", "Adults aged 18-65"),
])
def test_optional_dataset_fields(field_name, field_value):
    """Test optional dataset fields coverage"""
    # Create dataset with the specific optional field
    dataset = BASE_DATASET_TEMPLATE.copy()
    dataset[field_name] = field_value
    
    unmapped_objects = {
        'catalog': [BASE_CATALOG_TEMPLATE],
        'dataset': [dataset]
    }
    
    mapped_objects = map_xnat_to_healthriv2(unmapped_objects)
    
    # Check that the field was successfully mapped
    assert mapped_objects['dataset'][0]['uri'] == URIRef("http://localhost/data/archive/projects/test_img2catalog")
    mapped_dataset = mapped_objects['dataset'][0]['model_object']
    
    # Verify the field exists and has the correct value
    assert hasattr(mapped_dataset, field_name)
    mapped_value = getattr(mapped_dataset, field_name)

    if isinstance(field_value, list):
        str_mapped_value = [str(value) for value in mapped_value]
        assert str_mapped_value == field_value
    elif isinstance(mapped_value, LiteralField):
        assert mapped_value.value == field_value
    elif isinstance(field_value, str):
        assert str(mapped_value) == field_value
    else:
        assert mapped_value == field_value


@pytest.mark.parametrize("field_name,field_value", [
    # Complex fields that require special handling
    ("other_identifier", [{"notation": "ALT-ID-123", "schema_agency": "http://example.com/agency"}]),
    ("qualified_attribution", [{"agent": "http://example.com/agent1", "role": "http://example.com/role1"}]),
    ("qualified_relation", [{"had_role": ["http://example.com/role1"], "relation": ["http://example.com/relation1"]}]),
    ("quality_annotation", [{"target": "http://example.com/target1", "body": "http://example.com/body1"}]),
    ("retention_period", {"start_date": "2024-01-01", "end_date": "2025-01-01"}),
])
def test_complex_optional_dataset_fields(field_name, field_value):
    """Test complex optional dataset fields that create proper Pydantic objects"""
    # Create dataset with the specific complex field
    dataset = BASE_DATASET_TEMPLATE.copy()
    dataset[field_name] = field_value

    unmapped_objects = {
        'catalog': [BASE_CATALOG_TEMPLATE],
        'dataset': [dataset]
    }

    mapped_objects = map_xnat_to_healthriv2(unmapped_objects)

    # Check that the field was successfully mapped
    assert mapped_objects['dataset'][0]['uri'] == URIRef("http://localhost/data/archive/projects/test_img2catalog")
    mapped_dataset = mapped_objects['dataset'][0]['model_object']

    # Verify the field exists and has the correct value
    assert hasattr(mapped_dataset, field_name)
    mapped_value = getattr(mapped_dataset, field_name)
    
    # Special handling for different field types
    if field_name == "other_identifier":
        # Should be an Identifier object
        assert len(mapped_value) == 1
        assert mapped_value[0].notation == field_value[0]["notation"]
        assert mapped_value[0].schema_agency == field_value[0]["schema_agency"]
    elif field_name == "qualified_attribution":
        # Should be a list of Attribution objects
        assert len(mapped_value) == 1
        assert str(mapped_value[0].agent) == field_value[0]["agent"]
        assert str(mapped_value[0].role) == field_value[0]["role"]
    elif field_name == "qualified_relation":
        # Should be a list of Relationship objects
        assert len(mapped_value) == 1
        assert [str(role) for role in mapped_value[0].had_role] == field_value[0]["had_role"]
        assert [str(rel) for rel in mapped_value[0].relation] == field_value[0]["relation"]
    elif field_name == "quality_annotation":
        # Should be a list of QualityCertificate objects
        assert len(mapped_value) == 1
        assert str(mapped_value[0].target) == field_value[0]["target"]
        assert str(mapped_value[0].body) == field_value[0]["body"]
    elif field_name == "retention_period":
        # Should be a PeriodOfTime object
        assert mapped_value.start_date.value == field_value["start_date"]
        assert mapped_value.end_date.value == field_value["end_date"]


def test_minimal_required_fields_only():
    """Test mapping with only the minimum required fields (no optional fields)"""
    # Create dataset with only required fields
    minimal_dataset = {
        "contact_point": {
            "email": "mailto:minimal@example.com",
            "formatted_name": "Minimal Contact",
        },
        "creator": [{
            'identifier': ['http://example.com'],
            'name': ['Dr. Required Field'],
            'mbox': "mailto:required@example.com",
            'homepage': 'http://www.example.com'
        }],
        'publisher': {
            'identifier': ['http://www.example.com/institution#example'],
            'name': ['Example publishing institution'],
            'mbox': "example@example.com",
            'homepage': 'http://www.example.com'
        },
        "description": ['Minimal description'],
        "issued": datetime(2024, 4, 1, 0, 0),
        "identifier": "http://localhost/data/archive/projects/minimal",
        "keyword": ['minimal'],
        "modified": datetime(2024, 4, 1, 0, 0),
        'title': ["Minimal project"],
        "uri": "http://localhost/data/archive/projects/minimal",
        "access_rights": "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC",
        "applicable_legislation": ["http://data.europa.eu/eli/reg/2025/327/oj"],
        'theme': 'http://publications.europa.eu/resource/authority/data-theme/HEAL'
    }
    
    unmapped_objects = {
        'catalog': [BASE_CATALOG_TEMPLATE],
        'dataset': [minimal_dataset]
    }
    
    mapped_objects = map_xnat_to_healthriv2(unmapped_objects)
    
    # Should successfully map with only required fields
    assert mapped_objects['dataset'][0]['uri'] == URIRef("http://localhost/data/archive/projects/minimal")
    mapped_dataset = mapped_objects['dataset'][0]['model_object']
    
    # Verify required fields are present
    assert [title.value for title in mapped_dataset.title] == ["Minimal project"]
    assert [desc.value for desc in mapped_dataset.description] == ['Minimal description']
    assert [kw.value for kw in mapped_dataset.keyword] == ['minimal']
    assert len(mapped_dataset.creator) == 1
    assert mapped_dataset.creator[0].name == ['Dr. Required Field']
    
    # Verify optional fields are not set (should be None or default values)
    assert mapped_dataset.license is None
    assert mapped_dataset.maximum_typical_age is None
    assert mapped_dataset.minimum_typical_age is None


def test_maximum_fields_populated():
    """Test mapping with maximum number of optional fields populated"""
    # Create dataset with many optional fields
    maximal_dataset = {
        **BASE_DATASET_TEMPLATE,
        # Add many optional fields
        "publisher": {
            'identifier': ['http://example.com'],
            'name': ['Maximal Publisher'],
            'mbox': "mailto:publisher@example.com",
            'homepage': 'http://www.example.com'
        },
        "theme": ["http://publications.europa.eu/resource/authority/data-theme/HEAL"],
        "license": "http://example.com/license",
        "maximum_typical_age": 95,
        "minimum_typical_age": 18,
        "number_of_records": 10000,
        "number_of_unique_individuals": 5000,
        "population_coverage": "European adults",
        "health_theme": ["http://example.com/health1", "http://example.com/health2"],
        "personal_data": ["http://example.com/personal1"],
        "purpose": ["http://example.com/research"],
        "legal_basis": ["http://example.com/consent"],
        "analytics": ["http://example.com/analytics1"],
        "code_values": ["http://example.com/icd10"],
        "coding_system": ["http://example.com/snomed"],
        "conforms_to": ["http://example.com/standard1"],
        "documentation": ["http://example.com/docs"],
        "frequency": "http://example.com/monthly",
        "status": 'http://publications.europa.eu/resource/authority/dataset-status/COMPLETED'
    }
    
    unmapped_objects = {
        'catalog': [BASE_CATALOG_TEMPLATE],
        'dataset': [maximal_dataset]
    }
    
    mapped_objects = map_xnat_to_healthriv2(unmapped_objects)
    
    # Should successfully map with all fields
    assert mapped_objects['dataset'][0]['uri'] == URIRef("http://localhost/data/archive/projects/test_img2catalog")
    mapped_dataset = mapped_objects['dataset'][0]['model_object']
    
    # Verify key optional fields are correctly mapped
    assert mapped_dataset.publisher.name == ['Maximal Publisher']
    assert mapped_dataset.theme == [URIRef("http://publications.europa.eu/resource/authority/data-theme/HEAL")]
    assert str(mapped_dataset.license) == "http://example.com/license"
    assert mapped_dataset.maximum_typical_age == 95
    assert mapped_dataset.minimum_typical_age == 18
    assert mapped_dataset.number_of_records == 10000
    assert mapped_dataset.number_of_unique_individuals == 5000
    assert mapped_dataset.population_coverage.value == "European adults"
    assert [str(theme) for theme in mapped_dataset.health_theme] == ["http://example.com/health1", "http://example.com/health2"]
    assert [str(pd) for pd in mapped_dataset.personal_data] == ["http://example.com/personal1"]
    assert [str(purpose) for purpose in mapped_dataset.purpose] == ["http://example.com/research"]
    assert str(mapped_dataset.frequency) == "http://example.com/monthly"
    assert str(mapped_dataset.status) == 'http://publications.europa.eu/resource/authority/dataset-status/COMPLETED'


def test_mixed_optional_fields():
    """Test mapping with a mix of some optional fields present and some missing"""
    # Create dataset with selective optional fields
    mixed_dataset = {
        **BASE_DATASET_TEMPLATE,
        # Include some optional fields
        "maximum_typical_age": 80,
        "minimum_typical_age": 25,
        "health_theme": ["http://example.com/cardiology"],
        "frequency": "http://example.com/yearly",
        # Deliberately omit other optional fields like publisher, license, etc.
    }
    
    unmapped_objects = {
        'catalog': [BASE_CATALOG_TEMPLATE],
        'dataset': [mixed_dataset]
    }
    
    mapped_objects = map_xnat_to_healthriv2(unmapped_objects)
    
    # Should successfully map with mixed fields
    assert mapped_objects['dataset'][0]['uri'] == URIRef("http://localhost/data/archive/projects/test_img2catalog")
    mapped_dataset = mapped_objects['dataset'][0]['model_object']
    
    # Verify included optional fields
    assert mapped_dataset.maximum_typical_age == 80
    assert mapped_dataset.minimum_typical_age == 25
    assert [str(theme) for theme in mapped_dataset.health_theme] == ["http://example.com/cardiology"]
    assert str(mapped_dataset.frequency) == "http://example.com/yearly"
    
    # Verify excluded optional fields are None
    assert mapped_dataset.license is None
    assert mapped_dataset.personal_data is None
    assert mapped_dataset.purpose is None
