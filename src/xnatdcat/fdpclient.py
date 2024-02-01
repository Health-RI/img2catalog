import logging
from typing import Dict, Union
from urllib.parse import urljoin, urlparse

import requests
from rdflib import DCAT, RDF, Graph, URIRef
from requests import HTTPError, Response

logger = logging.getLogger(__name__)

# This file is taken from cedar2fdp


class BasicAPIClient:
    """Basic class for API client"""

    def __init__(self, base_url, headers):
        self.base_url = base_url
        self.headers = headers
        self.session = requests.session()
        self.session.headers.update(self.headers)
        self.ssl_verification = None

    def _call_method(self, method, path, params: Dict = None, data=None) -> Response:
        if method.upper() not in ["GET", "POST", "PUT", "DELETE"]:
            raise ValueError(f"Unsupported method {method}")
        url = urljoin(self.base_url, path)
        response = None
        # try:
        response = self.session.request(method, url, params=params, data=data, verify=self.ssl_verification)

        try:
            response.raise_for_status()
        except HTTPError as e:
            logger.error("%d %s: %s", e.response.status_code, e.response.reason, e.response.text)
            raise e

        return response

        # Commented this out, as I don't mind having the exceptions go through the stack
        # except requests.exceptions.HTTPError as e:
        #     logger.error(e)
        #     if response is not None:
        #         logger.error(response.text)
        #     # sys.exit(1)
        # except requests.exceptions.ConnectionError as e:
        #     logger.error(e)
        #     # sys.exit(1)
        # except requests.exceptions.Timeout as e:
        #     logger.error(e)
        #     # sys.exit(1)
        # except requests.exceptions.RequestException as e:
        #     logger.error(e)
        #     # sys.exit(1)
        # except Exception as e:

    def get(self, path: str, params: Dict = None) -> Response:
        return self._call_method("GET", path, params=params)

    def post(self, path: str, params: Dict = None, data=None) -> Response:
        return self._call_method("POST", path, params=params, data=data)

    def update(self, path: str, params: Dict = None, data=None) -> Response:
        return self._call_method("PUT", path, params=params, data=data)

    def delete(self, path: str, params: Dict = None, data=None) -> Response:
        return self._call_method("DELETE", path, params=params, data=data)


class FDPEndPoints:
    meta = "meta"
    state = f"{meta}/state"
    members = "members"
    expanded = "expanded"


class FDPClient(BasicAPIClient):
    """Client for FAIR Data Point client"""

    def __init__(self, base_url: str, username: str, password: str):
        """Initializes an FDP Client object

        Parameters
        ----------
        base_url : str
            Base URL of the Fair Data Point
        username : str
            username for authentication
        password : str
            password for authentication
        """
        self.base_url = base_url
        self.username = username
        # Don't store password for security reasons (might show up in a stack trace or something)
        # self.password = password
        self.__token = self.login_fdp(username, password)
        headers = self.get_headers()
        super().__init__(base_url, headers)

    def login_fdp(self, username: str, password: str) -> str:
        """Logs in to a Fair Data Point and retrieves a JWT token

        Parameters
        ----------
        username : str
            username for authentication
        password : str
            password for authentication

        Returns
        -------
        str
            JWT authentication token
        """
        token_response = requests.post(
            f"{self.base_url}/tokens",
            json={"email": username, "password": password},
        )
        token_response.raise_for_status()
        response = token_response.json()
        token = response["token"]
        self.__token = token
        return token

    def get_headers(self):
        return {"Authorization": f"Bearer {self.__token}", "Content-Type": "text/turtle"}

    def _update_session_headers(self):
        self.session.headers.update(self.headers)

    def _change_content_type(self, content_type):
        self.headers["Content-Type"] = content_type
        self._update_session_headers()

    def post_serialized(self, resource_type: str, metadata: "Graph") -> requests.Response:
        """Serializes and posts a graph to an FDP

        Parameters
        ----------
        resource_type : str
            Type of resource to push (e.g. 'dataset')
        metadata : Graph
            The graph with metadata to be pusshed

        Returns
        -------
        requests.Response
            The response from the FDP
        """
        self._change_content_type("text/turtle")
        path = f"{self.base_url}/{resource_type}"
        response = self.post(path=path, data=metadata.serialize(format="turtle"))
        return response

    def get_data(self, path: str) -> requests.Response:
        response = self.get(path=path)
        return response

    def delete_record(self, path: str) -> requests.Response:
        response = self.delete(path=path)
        return response

    def publish_record(self, record_url: str):
        """Changes the status of an FDP record to "Published"

        Parameters
        ----------
        record_url : str
            URL of the record that is to be published
        """
        self._change_content_type("application/json")
        path = f"{record_url}/{FDPEndPoints.state}"
        data = '{"current": "PUBLISHED"}'
        self.update(path=path, data=data)

    def create_and_publish(self, resource_type: str, metadata: "Graph") -> URIRef:
        """Creates and publishes a record in the FDP

        Parameters
        ----------
        resource_type : str
            Type of record to publish (e.g. Catalog, Distribution, Dataset)
        metadata : Graph
            The metadata to be published

        Returns
        -------
        URIRef
            URI of (subject of) published dataset
        """
        post_response = self.post_serialized(resource_type=resource_type, metadata=metadata)

        # Get FDP uuid (subject) (can we always assume it is the first? No we cannot)
        # fdp_subject = [x for x in Graph().parse(data=post_response.text).subjects() if isinstance(x, URIRef)][0]
        fdp_subject = Graph().parse(data=post_response.text).value(predicate=RDF.type, object=DCAT.Resource, any=False)
        fdp_path = urlparse(fdp_subject).path

        # Unclear what this is for?
        if fdp_path.count("/") > 2:
            fdp_path = fdp_path.rsplit("/", maxsplit=2)[0]

        fdp_subject = URIRef(f"{self.base_url}{fdp_path}")

        # Change status to 'published' so that metadata shows in catalog
        self.publish_record(fdp_subject)

        return fdp_subject
