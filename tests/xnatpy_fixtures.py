####
# Below code is taken from XNATPy, under the Apache 2.0 license
# (C) BIGR, ErasmusMC
# Included as xnat.tests isn't default
import contextlib
import logging
import os
from typing import Any, Pattern, Union
from urllib.parse import urlparse

import requests
import pytest
import xnat

from pytest_mock import MockerFixture
from requests import Response
from requests_mock import Mocker
from xnat.session import XNATSession

import xnat4tests
from xnat4tests import start_xnat, stop_xnat, add_data, Config, connect
from xnat4tests.utils import set_loggers

try:
    import docker
    DOCKER_IMPORTED = True
except ImportError:
    docker = None
    DOCKER_IMPORTED = False


logger = logging.getLogger(__name__)

class CreatedObject:
    def __init__(self, uri, type_, fieldname, **kwargs):
        self.uri = uri
        self.type = type_
        self.fieldname = fieldname
        self.kwargs = kwargs


class XnatpyRequestsMocker(Mocker):
    def request(self, method: str, url: Union[str, Pattern[str]], **kwargs: Any) -> Response:
        url = f"https://xnat.example.com/{url.lstrip('/')}"
        return super().request(method, url, **kwargs)


@pytest.fixture(scope="function")
def xnatpy_mock() -> XnatpyRequestsMocker:
    with XnatpyRequestsMocker() as mocker:
        yield mocker


@pytest.fixture(scope="function")
def xnatpy_connection(mocker: MockerFixture, xnatpy_mock: XnatpyRequestsMocker) -> XNATSession:
    # Create a working mocked XNATpy connection object
    threading_patch = mocker.patch("xnat.session.threading")  # Avoid background threads getting started
    # logger = logging.getLogger('xnatpy_test')

    xnatpy_mock.get("/data/JSESSION")
    xnatpy_mock.delete("/data/JSESSION")
    xnatpy_mock.get("/data/version", status_code=404)
    xnatpy_mock.get(
        "/xapi/siteConfig/buildInfo",
        json={
            "version": "1.7.5.6",
            "buildNumber": "1651",
            "buildDate": "Tue Aug 20 18:10:41 CDT 2019",
            "sha": "5696414138",
            "isDirty": "false",
            "commit": "2",
            "tag": "1.7.5.4",
            "shaFull": "5696414138d8c95288bf45c8eac2150ba041e867",
            "branch": "master",
            "timestamp": "1566342641000",
        },
    )
    requests_session = requests.Session()

    # Set cookie for JSESSION/timeout
    cookie = requests.cookies.create_cookie(
        domain="xnat.example.com",
        name="JSESSIONID",
        value="3EFD012EF2FA60EF44BA72ED5925F074",
    )
    requests_session.cookies.set_cookie(cookie)

    cookie = requests.cookies.create_cookie(
        domain="xnat.example.com",
        name="SESSION_EXPIRATION_TIME",
        value='"1668081619871,900000"',
    )
    requests_session.cookies.set_cookie(cookie)

    xnat_session = XNATSession(
        server="https://xnat.example.com",
        logger=logger,
        interface=requests_session,
    )

    # Patch create object to avoid a lot of hassle
    def create_object(uri, type_=None, fieldname=None, **kwargs):
        return CreatedObject(uri, type_, fieldname, **kwargs)

    xnat_session.create_object = create_object

    yield xnat_session

    # Close connection before the mocker gets cleaned
    xnat_session.disconnect()

    # Clean mocker
    xnatpy_mock.reset()

    # Stop patch of threading
    mocker.stop(threading_patch)


# Fixtures for xnat4tests, setup a config, use the pytest tmp_path_factory fixture for the tmpdir
@pytest.fixture(scope="session")
def xnat4tests_config(tmp_path_factory) -> Config:
    tmp_path = tmp_path_factory.mktemp('config')

    docker_host = os.environ.get('DOCKER_HOST')
    if docker_host:
        print(f'Docker host set in environment set to {docker_host}.')
        docker_host = urlparse(docker_host).netloc.split(':')[0]
    else:
        print('No docker host set in environment, using localhost as default.')
        docker_host = 'localhost'
    print(f'Determined docker hostname to be {docker_host}')

    set_loggers(loglevel='INFO')
    yield Config(
        xnat_root_dir=tmp_path,
        xnat_port=8080,
        docker_image="xnatpy_xnat4tests",
        docker_container="xnatpy_xnat4tests",
        docker_host=docker_host,
        build_args={
            "xnat_version": "1.8.5",
            "xnat_cs_plugin_version": "3.2.0",
        },
        connection_attempts=15,
        connection_attempt_sleep=10,
    )


# Fixtures for xnat4tests, start up a container and get the URI
@pytest.fixture(scope="session")
def xnat4tests_uri(xnat4tests_config) -> str:
    with xnat4tests_fixture(xnat4tests_config):
        yield xnat4tests_config.xnat_uri


######


# Create a context to ensure closure
@contextlib.contextmanager
def xnat4tests_fixture(config) -> str:
    start_xnat(config_name=config)
    try:
        # add_data("dummydicom", config_name=config)
        # add_data("user-training", config_name=config)
        project_dicts = [
            {'project_id': 'public_optout', 'accessibility': 'public', 'keywords': 'exclude_catalogue xnat'},
            {'project_id': 'public_optin', 'accessibility': 'public', 'keywords': 'include_catalogue xnat'},
            {'project_id': 'public_nokeyword', 'accessibility': 'public', 'keywords': ''},
            {'project_id': 'protected_optin', 'accessibility': 'protected', 'keywords': 'include_catalogue xnat'},
            {'project_id': 'private_optin', 'accessibility': 'private', 'keywords': 'include_catalogue xnat'}
        ]
        with xnat4tests.connect(config) as login:
            for project_dict in project_dicts:
                login.put(f"/data/archive/projects/{project_dict['project_id']}")
                login.put(f"/data/archive/projects/{project_dict['project_id']}/accessibility/{project_dict['accessibility']}")
        with xnat.connect(config.xnat_uri, user='admin', password='admin') as connection:
            connection.post("/xapi/investigators", json={
                "title" : "Prof.",
                "firstname" : "Example",
                "lastname" : "Exampleton",
                "email": "email@example.com"
            })
            for project_dict in project_dicts:
                project = connection.projects[project_dict['project_id']]
                project.description = f"{project_dict['project_id']}"
                project.keywords = project_dict['keywords']
                connection.put(f"/data/projects/{project_dict['project_id']}?pi_firstname=Example&pi_lastname=Exampleton")

        yield config.xnat_uri
    finally:
        stop_xnat(config_name=config)


# Fixtures for xnat4tests, create an xnatpy connection
@pytest.fixture(scope="session")
def xnat4tests_connection(xnat4tests_uri) -> XNATSession:
    # with xnat.connect(xnat4tests_uri) as connection:
    with xnat.connect(xnat4tests_uri, user='admin', password='admin') as connection:
        yield connection
