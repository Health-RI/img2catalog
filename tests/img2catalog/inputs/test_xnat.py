from datetime import datetime
from typing import Dict, Any
from unittest.mock import patch

import pytest
from freezegun import freeze_time
from rdflib import Graph
from requests_mock import Mocker
from xnat import XNATSession

from img2catalog.inputs import xnat as inputs_xnat
from img2catalog.inputs.config import ConfigInput
from img2catalog.inputs.xnat import XNATInput, filter_keyword, XNATParserError
from requests.exceptions import ConnectionError


@patch("xnat.core.XNATBaseObject")
@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("public", False),
        ("PUBLIC", False),
        ("protected", False),
        ("ProTected", False),
        ("private", True),
        ("Private", True),
    ],
)
def test_private_project_capitalization(
        project, test_input, expected, xnatpy_mock: Mocker, xnatpy_connection: XNATSession, config
):
    xnatpy_mock.get("/data/projects/example/accessibility", text=test_input)
    project.xnat_session = xnatpy_connection
    project.name = "example"
    project.uri = "/data/projects/example"

    xnat_input = XNATInput(config, xnatpy_connection)

    assert xnat_input._is_private_project(project) == expected


@patch("xnat.core.XNATBaseObject")
def test_private_project_invalid_value(project, xnatpy_mock: Mocker, xnatpy_connection: XNATSession, config):
    xnatpy_mock.get("/data/projects/example/accessibility", text="random_invalid_string_output")
    project.xnat_session = xnatpy_connection
    project.name = "example"
    project.uri = "/data/projects/example"
    xnat_input = XNATInput(config, xnatpy_connection)

    with pytest.raises(XNATParserError):
        xnat_input._is_private_project(project)


@patch("xnat.session.BaseXNATSession")
def test_empty_xnat_no_config(session, config: Dict[str, Any]):
    """Test case for an XNAT with no projects at all"""
    # XNATSession is a key-value store so pretend it is a Dict
    session.projects = {}
    session.url_for.return_value = "https://example.com"

    xnat_input = XNATInput(config, session)
    unmapped_objects = xnat_input.get_metadata()
    expected_unmapped_objects = {
        'catalog': [{'uri': "https://example.com", 'dataset': []}],
        'dataset': [],
    }

    assert unmapped_objects == expected_unmapped_objects


@patch("xnat.session.BaseXNATSession")
def test_empty_xnat(session, config: Dict[str, Any]):
    """Test case for an XNAT with no projects at all"""
    # XNATSession is a key-value store so pretend it is a Dict
    session.projects = {}
    session.url_for.return_value = "https://example.com"

    xnat_input = XNATInput(config, session)
    config_input = ConfigInput(config)
    unmapped_objects = xnat_input.get_and_update_metadata(config_input)
    expected_unmapped_objects = {
        'catalog': [
            {
                'uri': "https://example.com",
                'title': 'Example XNAT catalog',
                'description': 'This is an example XNAT catalog description',
                'publisher': {
                    'identifier': ['http://www.example.com/institution#example'],
                    'name': ['Example publishing institution'],
                    'mbox': 'mailto:publisher@example.com',
                    'homepage': 'http://www.example.com'
                },
                'contact_point': {
                    'formatted_name': 'Example Data Management office',
                    'email': 'mailto:datamanager@example.com'
                },
                'dataset': [],
            }
        ],
        'dataset': [],
    }
    assert unmapped_objects == expected_unmapped_objects

@freeze_time("2024-04-01")
@patch("xnat.session.BaseXNATSession")
@patch("xnat.core.XNATBaseObject")
@patch.object(XNATInput, "_check_eligibility_project", return_value=True)
def test_valid_project_no_investigator(mock_check_eligibility, session, project, config: Dict[str, Any], monkeypatch):
    """Test if a valid project generates valid output; only PI, no other investigators"""

    project.name = "Basic test project to test the img2catalog"
    project.description = "In this project, we test xnat and dcat and make sure a description appears."
    project.external_uri.return_value = "http://localhost/data/archive/projects/test_img2catalog"
    project.keywords = "test demo dcat"
    project.pi.firstname = "Albus"
    project.pi.lastname = "Dumbledore"
    project.pi.title = "prof."
    project.investigators = False

    session.projects = {'example_project': project}
    session.url_for.return_value = "https://example.com"

    xnat_input = XNATInput(config, session)
    config_input = ConfigInput(config)
    unmapped_objects = xnat_input.get_and_update_metadata(config_input)

    expected_unmapped_objects = {
        'catalog' : [{
            'uri': "https://example.com",
            'title': 'Example XNAT catalog',
            'description': 'This is an example XNAT catalog description',
            'publisher': {
                'identifier': ['http://www.example.com/institution#example'],
                'name': ['Example publishing institution'],
                'mbox': 'mailto:publisher@example.com',
                'homepage': 'http://www.example.com'
            },
            'dataset': ["http://localhost/data/archive/projects/test_img2catalog"],
            "contact_point": {
                "email": "mailto:datamanager@example.com",
                "formatted_name": "Example Data Management office"
            },
        }],
        'dataset': [{
            "access_rights": "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC",
            "applicable_legislation": ["http://data.europa.eu/eli/reg/2025/327/oj"],
            "contact_point": {
                "email": "mailto:datamanager@example.com",
                "formatted_name": "Example Data Management office"
            },
            "creator": [{
                'identifier': ['http://example.com'],
                'name': ['prof. Albus Dumbledore'],
                'mbox': 'mailto:example@example.com',
                'homepage': 'http://www.example.com'
            }],
            "description": ["In this project, we test xnat and dcat and make sure a description appears."],
            "issued": datetime(2024, 4, 1, 0, 0),
            "identifier": "http://localhost/data/archive/projects/test_img2catalog",
            "keyword": ['test', 'demo', 'dcat'],
            "modified": datetime(2024, 4, 1, 0, 0),
            "publisher": {
                'identifier': ['http://example.com'],
                'name': ['Example publisher list'],
                'mbox': 'mailto:publisher@example.com',
                'homepage': 'http://www.example.com'
            },
            'theme': 'http://publications.europa.eu/resource/authority/data-theme/HEAL',
            'title': ["Basic test project to test the img2catalog"],
            "uri": "http://localhost/data/archive/projects/test_img2catalog",
        }]
    }

    assert unmapped_objects == expected_unmapped_objects


@freeze_time("2024-04-01")
@patch("xnat.session.BaseXNATSession")
@patch("xnat.core.XNATBaseObject")
@patch.object(XNATInput, "_check_eligibility_project", return_value=True)
def test_valid_project(mock_check_eligibility, session, project, config: Dict[str, Any]):
    """Test if a valid project generates valid output; multiple investigators"""
    class InvestigatorDataclass:
        def __init__(self, firstname, lastname, title):
            self.firstname = firstname
            self.lastname = lastname
            self.title = title

    project.name = "Basic test project to test the img2catalog"
    # project.description = "In this project, we test &quot;xnat&quot; &amp; dcat and make sure a description appears."
    project.description = 'In this project, we test "xnat" & dcat and make sure a description appears.'
    project.external_uri.return_value = "http://localhost/data/archive/projects/test_img2catalog"
    project.keywords = "test demo dcat"
    project.pi.firstname = "Albus"
    project.pi.lastname = "Dumbledore"
    project.pi.title = "prof."
    # project
    project.investigators = [InvestigatorDataclass(firstname="Minerva", lastname="McGonagall", title="Prof.")]

    session.projects = {'example_project': project}
    session.url_for.return_value = "https://example.com"

    xnat_input = XNATInput(config, session)
    config_input = ConfigInput(config)
    unmapped_objects = xnat_input.get_and_update_metadata(config_input)

    expected_unmapped_objects = {
        'catalog' : [{
            'uri': "https://example.com",
            'title': 'Example XNAT catalog',
            'description': 'This is an example XNAT catalog description',
            'publisher': {
                'identifier': ['http://www.example.com/institution#example'],
                'name': ['Example publishing institution'],
                'mbox': 'mailto:publisher@example.com',
                'homepage': 'http://www.example.com'
            },
            'dataset': ["http://localhost/data/archive/projects/test_img2catalog"],
            "contact_point": {
                "email": "mailto:datamanager@example.com",
                "formatted_name": "Example Data Management office"
            },
        }],
        'dataset': [{
            "access_rights": "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC",
            "applicable_legislation": ["http://data.europa.eu/eli/reg/2025/327/oj"],
            "contact_point": {
                "email": "mailto:datamanager@example.com",
                "formatted_name": "Example Data Management office",
            },
            "creator": [
                {
                'identifier': ['http://example.com'],
                'name': ['prof. Albus Dumbledore'],
                'mbox': 'mailto:example@example.com',
                'homepage': 'http://www.example.com'
                },
                {
                    'identifier': ['http://example.com'],
                    'name': ['Prof. Minerva McGonagall'],
                    'mbox': 'mailto:example@example.com',
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
                'mbox': 'mailto:publisher@example.com',
                'homepage': 'http://www.example.com'
            },
            'theme': 'http://publications.europa.eu/resource/authority/data-theme/HEAL',
            'title': ["Basic test project to test the img2catalog"],
            "uri": "http://localhost/data/archive/projects/test_img2catalog",
        }]
    }

    assert unmapped_objects == expected_unmapped_objects


@freeze_time("2024-04-01")
@patch("xnat.session.BaseXNATSession")
@patch("xnat.core.XNATBaseObject")
@patch.object(XNATInput, "_check_eligibility_project", return_value=True)
def test_no_keywords(mock_check_eligibility, session, project, empty_graph: Graph, config: Dict[str, Any]):
    """Valid project without keywords, make the property `keywords` it is not defined in output"""

    project.name = "Basic test project to test the img2catalog"
    project.description = "In this project, we test xnat and dcat and make sure a description appears."
    project.external_uri.return_value = "http://localhost/data/archive/projects/test_img2catalog"
    project.keywords = ""
    project.pi.firstname = "Albus"
    project.pi.lastname = "Dumbledore"
    project.pi.title = "prof."
    project.investigators = False


    session.projects = {'example_project': project}
    session.url_for.return_value = "https://example.com"

    xnat_input = XNATInput(config, session)
    config_input = ConfigInput(config)
    unmapped_objects = xnat_input.get_and_update_metadata(config_input)

    expected_unmapped_objects = {
        'catalog' : [{
            'uri': "https://example.com",
            'title': 'Example XNAT catalog',
            'description': 'This is an example XNAT catalog description',
            'publisher': {
                'identifier': ['http://www.example.com/institution#example'],
                'name': ['Example publishing institution'],
                'mbox': 'mailto:publisher@example.com',
                'homepage': 'http://www.example.com'
            },
            'dataset': ["http://localhost/data/archive/projects/test_img2catalog"],
            "contact_point": {
                "email": "mailto:datamanager@example.com",
                "formatted_name": "Example Data Management office"
            },
        }],
        'dataset': [{
            "access_rights": "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC",
            "applicable_legislation": ["http://data.europa.eu/eli/reg/2025/327/oj"],
            "contact_point": {
                "email": "mailto:datamanager@example.com",
                "formatted_name": "Example Data Management office",
            },
            "creator": [
                {
                    'identifier': ['http://example.com'],
                    'name': ['prof. Albus Dumbledore'],
                    'mbox': 'mailto:example@example.com',
                    'homepage': 'http://www.example.com'
                }
            ],
            "description": ['In this project, we test xnat and dcat and make sure a description appears.'],
            "issued": datetime(2024, 4, 1, 0, 0),
            "identifier": "http://localhost/data/archive/projects/test_img2catalog",
            "keyword": [],
            "modified": datetime(2024, 4, 1, 0, 0),
            "publisher": {
                'identifier': ['http://example.com'],
                'name': ['Example publisher list'],
                'mbox': 'mailto:publisher@example.com',
                'homepage': 'http://www.example.com'
            },
            'theme': 'http://publications.europa.eu/resource/authority/data-theme/HEAL',
            'title': ["Basic test project to test the img2catalog"],
            "uri": "http://localhost/data/archive/projects/test_img2catalog",
        }]
    }

    assert unmapped_objects == expected_unmapped_objects


@freeze_time("2024-04-01")
@patch("xnat.session.BaseXNATSession")
@patch("xnat.core.XNATBaseObject")
@patch.object(XNATInput, "_check_eligibility_project", return_value=True)
def test_no_pi(mock_check_eligibility, session, project, empty_graph: Graph, config: Dict[str, Any]):
    """Valid project without keywords, make the property `keywords` it is not defined in output"""

    project.name = "Basic test project to test the img2catalog"
    project.description = "In this project, we test xnat and dcat and make sure a description appears."
    project.external_uri.return_value = "http://localhost/data/archive/projects/test_img2catalog"
    project.keywords = ""
    project.pi.firstname = None
    project.pi.lastname = None
    project.investigators = False

    session.projects = {'example_project': project}
    session.url_for.return_value = "https://example.com"

    xnat_input = XNATInput(config, session)
    with pytest.raises(XNATParserError) as exc:
        _ = xnat_input.project_to_dataset(project)


@freeze_time("2024-04-01")
@patch("xnat.session.BaseXNATSession")
@patch("xnat.core.XNATBaseObject")
@patch.object(XNATInput, "_check_eligibility_project", return_value=True)
def test_no_description(mock_check_eligibility, session, project, empty_graph: Graph, config: Dict[str, Any]):
    """Valid project without keywords, make the property `keywords` it is not defined in output"""

    project.name = "Basic test project to test the img2catalog"
    project.description = None
    project.external_uri.return_value = "http://localhost/data/archive/projects/test_img2catalog"
    project.keywords = ""
    project.pi.firstname = "Albus"
    project.pi.lastname = "Dumbledore"
    project.pi.title = "prof."
    project.investigators = False

    session.projects = {'example_project': project}
    session.url_for.return_value = "https://example.com"

    xnat_input = XNATInput(config, session)
    with pytest.raises(XNATParserError) as exc:
        _ = xnat_input.project_to_dataset(project)

@pytest.mark.parametrize(
    "private, optin, expected", [
        (False, True, True),
        (True, True, False),
        (False, False, False),
        (True, False, False),
    ]
)
@patch("xnat.core.XNATBaseObject")
@patch.object(XNATInput, "_is_private_project")
@patch.object(inputs_xnat, "check_optin_optout")
def test_project_eligibility(mock_check_optin_optout, mock_is_private_project, project, private, optin, expected):
    """ Test project eligibility; it should only be eligible if it's not private, but does have opt-in. """
    mock_is_private_project.return_value = private
    mock_check_optin_optout.return_value = optin

    project.__str__.return_value = "test project"
    project.id = "test"

    xnat_input = XNATInput({}, None)

    assert xnat_input._check_eligibility_project(project) == expected


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


@pytest.mark.parametrize(
    "keywords, config, expected",
    [
        # Test fallback keywords with empty list
        ([], {"img2catalog": {"fallback_keywords": ["default", "fallback"]}}, ["default", "fallback"]),
        # Test fallback keywords with None
        (None, {"img2catalog": {"fallback_keywords": ["default", "fallback"]}}, ["default", "fallback"]),
        # Test fallback keywords as string
        ([], {"img2catalog": {"fallback_keywords": "single"}}, ["single"]),
        # Test no fallback when keywords exist
        (["existing"], {"img2catalog": {"fallback_keywords": ["default", "fallback"]}}, ["existing"]),
        # Test fallback when only optin keyword is removed
        (["optin"], {"img2catalog": {"optin": "optin", "fallback_keywords": ["default"]}}, ["default"]),
        # Test no fallback when no config
        ([], {}, []),
        # Test no fallback when fallback_keywords not configured
        ([], {"img2catalog": {}}, []),
        # Test fallback combined with optin removal
        (["keep", "optin"], {"img2catalog": {"optin": "optin", "fallback_keywords": ["default"]}}, ["keep"]),
    ],
)
def test_keyword_filter_fallback(keywords, config, expected):
    result = filter_keyword(keywords, config)
    assert sorted(result) == sorted(expected)


@patch("xnat.session.BaseXNATSession")
def test_xnat_lister(mock_session):
    """ Test if `xnat_list_datasets` returns the right datasets based on eligibility and errors"""
    class SimpleProject:
        def __init__(self, project_id):
            self.id = None
            self.name = project_id

    # xnat_list_datasets
    mock_session.projects.values.return_value = [
        SimpleProject("p1"),
        SimpleProject("p2"),
        SimpleProject("p3"),
        SimpleProject("p4"),
    ]
    xnat_input = XNATInput({}, mock_session)
    with patch.object(xnat_input, "project_to_dataset", side_effect=[
             {"name": "p1", "identifier": "project_1"},
             None,
             {"name": "p3", "identifier": "project_3"},
             XNATParserError("Test error", ["This project cannot be converted"]),
         ]):

        list_result = xnat_input.get_metadata_datasets()

        assert list_result == [
            {"name": "p1", "identifier": "project_1"},
            {"name": "p3", "identifier": "project_3"}
        ]

        assert xnat_input.project_to_dataset.call_count == 4


# Custom Form Tests
@patch("xnat.core.XNATBaseObject")
def test_get_custom_form_metadata_success(project, xnatpy_mock: Mocker, xnatpy_connection: XNATSession):
    """Test successful custom form metadata retrieval with real API response format"""
    config = {
        'xnat': {
            'dataset_form_id': 'e2c04eef-6333-41ae-8977-33e2f0793788'
        }
    }
    
    # Mock the custom form API response in the actual format
    custom_form_response = {
        '81057367-f72c-46d6-b6c2-1c409d49f61e': {
            'condition': '25370001 - Hepatocellular Carcinoma'
        },
        '9b82df19-6639-4b87-b851-850cbc809c06': {
            'test_key': False
        },
        'e2c04eef-6333-41ae-8977-33e2f0793788': {
            'submit': False,
            'creators': [
                {
                    'name': 'Prof. C. Reator',
                    'email': 'example@example.org',
                    'identifier': 'https://example.org'
                },
                {
                    'name': 'Hon. Example Exampleton',
                    'email': 'example2@example.org',
                    'identifier': 'https://example.org/0118-999'
                }
            ],
            'accessRights': 'restricted',
            'modificationDate': '2025-06-01T12:00:00+02:00',
            'maximumTypicalAge': 107,
            'minimumTypicalAge': 15
        }
    }
    
    project.id = "test_project"
    project.xnat_session = xnatpy_connection
    xnatpy_mock.get("/xapi/custom-fields/projects/test_project/fields", json=custom_form_response)
    
    xnat_input = XNATInput(config, xnatpy_connection)
    result = xnat_input.get_custom_form_metadata(project, 'dataset')
    
    expected = {
        'submit': False,
        'creators': [
            {
                'name': 'Prof. C. Reator',
                'email': 'example@example.org',
                'identifier': 'https://example.org'
            },
            {
                'name': 'Hon. Example Exampleton',
                'email': 'example2@example.org',
                'identifier': 'https://example.org/0118-999'
            }
        ],
        'accessRights': 'restricted',
        'modificationDate': '2025-06-01T12:00:00+02:00',
        'maximumTypicalAge': 107,
        'minimumTypicalAge': 15
    }
    
    assert result == expected


@patch("xnat.core.XNATBaseObject")
def test_get_custom_form_metadata_no_config(project, xnatpy_connection: XNATSession):
    """Test custom form metadata retrieval when no custom form ID is configured"""
    config = {}
    xnat_input = XNATInput(config, xnatpy_connection)
    
    result = xnat_input.get_custom_form_metadata(project, 'dataset')
    
    assert result == {}


@patch("xnat.core.XNATBaseObject")
def test_get_custom_form_metadata_form_not_found(project, xnatpy_mock: Mocker, xnatpy_connection: XNATSession):
    """Test custom form metadata retrieval when form ID is not found"""
    config = {
        'xnat': {
            'dataset_form_id': 'nonexistent-form-id'
        }
    }
    
    custom_form_response = {
        '81057367-f72c-46d6-b6c2-1c409d49f61e': {
            'condition': '25370001 - Hepatocellular Carcinoma'
        }
    }
    
    project.name = "test_project"
    project.xnat_session = xnatpy_connection
    xnatpy_mock.get("/xapi/custom-fields/projects/test_project/fields", json=custom_form_response)
    
    xnat_input = XNATInput(config, xnatpy_connection)
    result = xnat_input.get_custom_form_metadata(project, 'dataset')
    
    assert result == {}


@patch("xnat.core.XNATBaseObject")
def test_get_custom_form_metadata_http_error(project, xnatpy_mock: Mocker, xnatpy_connection: XNATSession):
    """Test custom form metadata retrieval with HTTP error responses"""
    config = {
        'xnat': {
            'dataset_form_id': 'test-form-id'
        }
    }
    
    project.name = "test_project"
    project.xnat_session = xnatpy_connection
    xnatpy_mock.get("/xapi/custom-fields/projects/test_project/fields", status_code=404)
    
    xnat_input = XNATInput(config, xnatpy_connection)
    result = xnat_input.get_custom_form_metadata(project, 'dataset')
    
    assert result == {}


@patch("xnat.core.XNATBaseObject")
def test_get_custom_form_metadata_exception(project, xnatpy_mock: Mocker, xnatpy_connection: XNATSession):
    """Test custom form metadata retrieval with network exception"""
    config = {
        'xnat': {
            'dataset_form_id': 'test-form-id'
        }
    }
    
    project.name = "test_project"
    project.xnat_session = xnatpy_connection
    # Mock a network exception
    xnatpy_mock.get("/xapi/custom-fields/projects/test_project/fields", exc=ConnectionError("Network error"))
    
    xnat_input = XNATInput(config, xnatpy_connection)
    result = xnat_input.get_custom_form_metadata(project, 'dataset')
    
    assert result == {}


@patch("xnat.session.BaseXNATSession")
def test_apply_custom_form_metadata_project_not_found(session):
    """Test custom form application when project lookup fails"""
    config = {
        'xnat': {
            'dataset_form_id': 'test-form-id'
        }
    }
    
    # Mock session with missing project
    session.projects = {}
    
    metadata_objects = [{
        'uri': 'http://localhost/data/archive/projects/nonexistent_project',
        'title': ['Test Dataset']
    }]
    
    xnat_input = XNATInput(config, session)
    result = xnat_input.apply_custom_form_metadata(metadata_objects, 'dataset')
    
    # Should return original metadata unchanged
    assert result == metadata_objects


def test_apply_custom_form_metadata_non_dataset_concept():
    """Test custom form application for non-dataset concept types"""
    config = {
        'xnat': {
            'catalog_form_id': 'test-form-id'
        }
    }
    
    metadata_objects = [{
        'uri': 'http://localhost/catalog',
        'title': 'Test Catalog'
    }]
    
    xnat_input = XNATInput(config, None)
    result = xnat_input.apply_custom_form_metadata(metadata_objects, 'catalog')
    
    # Should return original metadata unchanged (catalog not supported)
    assert result == metadata_objects


def test_update_metadata_with_custom_form_empty_custom_data():
    """Test _update_metadata_with_custom_form with empty custom form data"""
    xnat_input = XNATInput({}, None)
    
    source_obj = {'title': ['Original Title'], 'description': ['Original Description']}
    custom_form_data = {}
    
    result = xnat_input._update_metadata_with_custom_form(source_obj, custom_form_data)
    
    # Should return original object unchanged
    assert result == source_obj


def test_update_metadata_with_custom_form_override_existing():
    """Test _update_metadata_with_custom_form overriding existing fields"""
    xnat_input = XNATInput({}, None)
    
    source_obj = {
        'title': ['Original Title'],
        'description': ['Original Description'],
        'keywords': ['original', 'keywords']
    }
    custom_form_data = {
        'title': 'Updated Title',  # Single value to list field
        'description': ['Updated Description'],  # List to list field
        'keywords': 'updated'  # Single value to existing list field
    }
    
    result = xnat_input._update_metadata_with_custom_form(source_obj, custom_form_data)
    
    expected = {
        'title': ['Updated Title'],  # Converted to list
        'description': ['Updated Description'],  # Kept as list
        'keywords': ['updated']  # Converted to list
    }
    
    assert result == expected


def test_update_metadata_with_custom_form_add_new_fields():
    """Test _update_metadata_with_custom_form adding new fields"""
    xnat_input = XNATInput({}, None)
    
    source_obj = {'title': ['Original Title']}
    custom_form_data = {
        'new_field': 'New Value',
        'another_field': ['List Value']
    }
    
    result = xnat_input._update_metadata_with_custom_form(source_obj, custom_form_data)
    
    expected = {
        'title': ['Original Title'],
        'new_field': 'New Value',
        'another_field': ['List Value']
    }
    
    assert result == expected


def test_update_metadata_with_custom_form_list_to_non_list():
    """Test _update_metadata_with_custom_form with list to non-list conversion"""
    xnat_input = XNATInput({}, None)
    
    source_obj = {'single_field': 'original_value'}
    custom_form_data = {
        'single_field': ['list', 'value']  # List to non-list field
    }
    
    result = xnat_input._update_metadata_with_custom_form(source_obj, custom_form_data)
    
    expected = {
        'single_field': ['list', 'value']  # Should replace with list
    }
    
    assert result == expected


@pytest.mark.parametrize("value, expected", [
    (None, True),
    ("", True),
    ("   ", True),  # Whitespace only string
    ("actual_value", False),
    ([], True),  # Empty list
    ([None], True),  # List with None
    (["", "   "], True),  # List with empty strings
    (["value"], False),  # List with actual value
    ([None, "value"], False),  # Mixed list with some valid values
    ({}, True),  # Empty dict
    ({"key": None}, True),  # Dict with None value
    ({"key": ""}, True),  # Dict with empty string
    ({"key": "value"}, False),  # Dict with actual value
    ({"key1": None, "key2": "value"}, False),  # Mixed dict
    ({"nested": {"inner": None}}, True),  # Nested empty dict
    ({"nested": {"inner": "value"}}, False),  # Nested dict with value
    (0, False),  # Zero is not empty
    (False, False),  # False is not empty
])
def test_is_empty_value(value, expected):
    """Test _is_empty_value with various data types"""
    xnat_input = XNATInput({}, None)
    result = xnat_input._is_empty_value(value)
    assert result == expected


def test_filter_empty_values():
    """Test _filter_empty_values with complex nested structures"""
    xnat_input = XNATInput({}, None)
    
    data = {
        'valid_string': 'keep_this',
        'empty_string': '',
        'whitespace_string': '   ',
        'none_value': None,
        'valid_list': ['item1', 'item2'],
        'empty_list': [],
        'list_with_empty': [None, '', 'valid'],
        'list_all_empty': [None, '', '   '],
        'valid_dict': {'nested': 'value'},
        'empty_dict': {},
        'dict_with_empty_values': {'key1': None, 'key2': ''},
        'dict_mixed': {'empty': None, 'valid': 'value'},
        'zero_value': 0,
        'false_value': False
    }
    
    result = xnat_input._filter_empty_values(data)
    
    expected = {
        'valid_string': 'keep_this',
        'valid_list': ['item1', 'item2'],
        'list_with_empty': [None, '', 'valid'],  # Keep lists with some valid items
        'valid_dict': {'nested': 'value'},
        'dict_mixed': {'empty': None, 'valid': 'value'},  # Keep dicts with some valid values
        'zero_value': 0,
        'false_value': False
    }
    
    assert result == expected


def test_filter_empty_values_nested_structures():
    """Test _filter_empty_values with deeply nested structures"""
    xnat_input = XNATInput({}, None)
    
    data = {
        'deeply_nested_empty': {
            'level1': {
                'level2': {
                    'level3': None
                }
            }
        },
        'deeply_nested_valid': {
            'level1': {
                'level2': {
                    'level3': 'value'
                }
            }
        },
        'mixed_nested': {
            'empty_branch': {'all': None},
            'valid_branch': {'some': 'value'}
        }
    }
    
    result = xnat_input._filter_empty_values(data)
    
    expected = {
        'deeply_nested_valid': {
            'level1': {
                'level2': {
                    'level3': 'value'
                }
            }
        },
        'mixed_nested': {
            'empty_branch': {'all': None},
            'valid_branch': {'some': 'value'}
        }
    }
    
    assert result == expected


@pytest.mark.parametrize("uri, expected", [
    ("http://localhost/data/archive/projects/test_project", "test_project"),
    ("https://xnat.example.com/projects/PROJECT_NAME", "PROJECT_NAME"),
    ("http://example.com/projects/my-project-123", "my-project-123"),
    ("https://server.org/some/path/projects/nested_project/extra", "nested_project/extra"),
    ("http://localhost/projects/", ""),  # Empty project name
    ("http://localhost/data/archive/datasets/test", None),  # No /projects/ in URI
    ("not_a_valid_uri", None),  # Invalid URI format
    ("", None),  # Empty string
    (None, None),  # None value
])
def test_extract_project_name_from_dataset_uri(uri, expected):
    """Test _extract_project_name_from_dataset_uri with various URI formats"""
    xnat_input = XNATInput({}, None)
    result = xnat_input._extract_project_name_from_dataset_uri(uri)
    assert result == expected


def test_extract_project_name_from_dataset_uri_non_string():
    """Test _extract_project_name_from_dataset_uri with non-string input"""
    xnat_input = XNATInput({}, None)
    
    # Test with non-string that would cause isinstance check to fail
    result = xnat_input._extract_project_name_from_dataset_uri(123)
    assert result is None
    
    # Test with object that doesn't have split method
    result = xnat_input._extract_project_name_from_dataset_uri(['not', 'a', 'string'])
    assert result is None


@freeze_time("2024-04-01")
@patch("xnat.session.BaseXNATSession")
@patch("xnat.core.XNATBaseObject")
@patch.object(XNATInput, "_check_eligibility_project", return_value=True)
def test_project_to_dataset_html_unescaping(mock_check_eligibility, session, project, config: Dict[str, Any]):
    """Test HTML entity unescaping in project descriptions"""
    
    project.name = "Test project with HTML entities"
    # HTML entities that should be unescaped
    project.description = 'Project with &quot;quotes&quot; &amp; ampersands &lt;tags&gt;'
    project.external_uri.return_value = "http://localhost/data/archive/projects/html_test"
    project.keywords = "test html entities"
    project.pi.firstname = "Test"
    project.pi.lastname = "User"
    project.pi.title = "Dr."
    project.investigators = False

    session.projects = {'html_test': project}
    session.url_for.return_value = "https://example.com"

    xnat_input = XNATInput(config, session)
    result = xnat_input.project_to_dataset(project)
    
    # Should unescape HTML entities in description
    expected_description = 'Project with "quotes" & ampersands <tags>'
    assert result['description'] == [expected_description]


@freeze_time("2024-04-01")
@patch("xnat.session.BaseXNATSession")
@patch("xnat.core.XNATBaseObject")
@patch.object(XNATInput, "_check_eligibility_project", return_value=True)
def test_project_to_dataset_string_project_name(mock_check_eligibility, session, project, config: Dict[str, Any]):
    """Test project_to_dataset with string project name instead of project object"""
    
    project.name = "String conversion test"
    project.description = "Testing string to project conversion"
    project.external_uri.return_value = "http://localhost/data/archive/projects/string_test"
    project.keywords = "test string conversion"
    project.pi.firstname = "Test"
    project.pi.lastname = "User"
    project.pi.title = "Dr."
    project.investigators = False

    session.projects = {'string_test': project}
    session.url_for.return_value = "https://example.com"

    xnat_input = XNATInput(config, session)
    
    # Test with string project name instead of project object
    result = xnat_input.project_to_dataset('string_test')
    
    assert result is not None
    assert result['title'] == ["String conversion test"]
    assert result['description'] == ["Testing string to project conversion"]


def test_parse_custom_form_response_filtering():
    """Test _parse_custom_form_response with mixed valid and empty data"""
    xnat_input = XNATInput({}, None)
    
    custom_fields_data = {
        'target_form_id': {
            'valid_field': 'valid_value',
            'empty_field': '',
            'none_field': None,
            'whitespace_field': '   ',
            'valid_list': ['item1', 'item2'],
            'empty_list': [],
            'mixed_list': [None, 'valid_item'],
            'zero_value': 0,
            'false_value': False
        },
        'other_form_id': {
            'should_not_appear': 'in_result'
        }
    }
    
    result = xnat_input._parse_custom_form_response(custom_fields_data, 'target_form_id')
    
    expected = {
        'valid_field': 'valid_value',
        'valid_list': ['item1', 'item2'],
        'mixed_list': [None, 'valid_item'],
        'zero_value': 0,
        'false_value': False
    }
    
    assert result == expected


@patch("xnat.session.BaseXNATSession")
def test_apply_custom_form_metadata_with_uri_none(session):
    """Test apply_custom_form_metadata when URI is None"""
    config = {
        'xnat': {
            'dataset_form_id': 'test-form-id'
        }
    }
    
    session.projects = {}
    
    metadata_objects = [{
        'uri': None,  # None URI should be handled gracefully
        'title': ['Test Dataset']
    }]
    
    xnat_input = XNATInput(config, session)
    result = xnat_input.apply_custom_form_metadata(metadata_objects, 'dataset')
    
    # Should return original metadata unchanged
    assert result == metadata_objects
