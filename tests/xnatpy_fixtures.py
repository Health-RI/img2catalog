####
# Below code is taken from XNATPy, under the Apache 2.0 license
# (C) BIGR, ErasmusMC
# Included as xnat.tests isn't default
import logging
from typing import Any, Pattern, Union

import requests
import pytest

from pytest_mock import MockerFixture
from requests import Response
from requests_mock import Mocker
from xnat.session import XNATSession

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


######
