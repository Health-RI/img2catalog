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
            'yup': False
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
    
    project.name = "test_project"
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
