import logging

import pytest
from unittest.mock import patch

from requests_mock import Mocker
from xnat.session import XNATSession

from img2catalog.xnat_parser import XNATParserError, xnat_private_project

logger = logging.getLogger(__name__)


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
    project, test_input, expected, xnatpy_mock: Mocker, xnatpy_connection: XNATSession
):
    xnatpy_mock.get("/data/projects/example/accessibility", text=test_input)
    project.xnat_session = xnatpy_connection
    project.name = "example"
    project.uri = "/data/projects/example"

    assert xnat_private_project(project) == expected


@patch("xnat.core.XNATBaseObject")
def test_private_project_invalid_value(project, xnatpy_mock: Mocker, xnatpy_connection: XNATSession):
    xnatpy_mock.get("/data/projects/example/accessibility", text="random_invalid_string_output")
    project.xnat_session = xnatpy_connection
    project.name = "example"
    project.uri = "/data/projects/example"

    with pytest.raises(XNATParserError):
        xnat_private_project(project)
