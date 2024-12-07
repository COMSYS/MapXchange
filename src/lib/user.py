"""
Base user for producers

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import logging
import time
import urllib3
from abc import ABC, abstractmethod
from typing import Iterable

import requests

from src.lib import config
from src.lib.helpers import print_time


log: logging.Logger = logging.getLogger(__name__)

KEYSERVER = f"https://{config.KEY_HOSTNAME}:{config.KEY_API_PORT}"
MAPSERVER = f"https://{config.MAP_HOSTNAME}:{config.MAP_API_PORT}"


class ServerType:
    """Types of server components"""

    KeyServer = "key_server"
    MapServer = "map_server"


class UserType:
    """Types of users"""

    Producer = "producer"


class User(ABC):
    """Abstract base class for end-user clients of producers"""

    username: str = None
    password: str = None
    keyserver: str = None
    mapserver: str = None
    eval = {}

    @property
    @abstractmethod
    def type(self) -> str:
        """A user has to be a producer, see UserType above."""

    def __init__(self, username: str) -> None:
        """Create object."""
        if not config.USE_TLS:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.user = username
        self.keyserver = KEYSERVER + "/" + self.type
        self.mapserver = MAPSERVER + "/" + self.type

    def get_auth_data(self, url: str) -> tuple[str, str]:
        """
        Return authentication information for authentication toward
        key or map server.

        :type url: URL to determine server from
        :return: (Username, Token)
        """
        if KEYSERVER in url:
            server_type = ServerType.KeyServer
        elif MAPSERVER in url:
            server_type = ServerType.MapServer
        else:
            raise ValueError(f"Unknown server type for url: {url}")
        return self.user, self.get_token(server_type)

    def get(self, url: str,
            auth: tuple[str, str] | None = None) -> requests.Response:
        """
        Perform a get request and check result.

        :param url: URL to request
        :param auth: Only if no token used for authentication
        :return: Response object
        """
        if auth is None:
            auth = self.get_auth_data(url)
        if config.USE_TLS:
            r = requests.get(url, verify=config.TLS_ROOT_CA, auth=auth)
        else:
            r = requests.get(url, verify=False, auth=auth)
        if r.status_code == 401:
            raise RuntimeError(
                f"Authentication failed at: {url}.")
        elif r.status_code != 200 and r.status_code != 202:
            r.raise_for_status()
        else:
            return r

    def post(self, url: str, json: dict | Iterable,
             auth: tuple[str, str] | None = None) -> requests.Response:
        """
        Perform a POST request and check result.

        :param url: URL to request
        :param json: JSON to transmit with request
        :param auth: Only if no token used for authentication
        :return: Response object
        """
        if auth is None:
            auth = self.get_auth_data(url)
        if config.USE_TLS:
            r = requests.post(url, verify=config.TLS_ROOT_CA, auth=auth, json=json)
        else:
            r = requests.post(url, verify=False, auth=auth, json=json)
        if r.status_code == 401:
            raise RuntimeError(
                f"Authentication failed at: {url}.")
        elif r.status_code != 200 and r.status_code != 202:
            r.raise_for_status()
        else:
            return r

    def set_password(self, pwd: str) -> None:
        """
        Set password for this user.

        :param pwd: Password of this user
        """
        self.password = pwd

    def get_token(self, server_type: str) -> str:
        """
        Retrieve a token from the given server.

        :param server_type: Type of server to get the token from
        :return: Token as string, can be used for authentication as is
        """
        log.debug("Get token from key server.")
        if self.password is None:
            raise ValueError("To retrieve a token, the user has to be "
                             "authenticated.")
        if server_type == ServerType.MapServer:
            server = self.mapserver
        elif server_type == ServerType.KeyServer:
            server = self.keyserver
        else:
            raise ValueError(f"No server of type '{server_type}' exists.")
        r = self.get(
            f"{server}/gen_token",
            auth=(self.user, self.password))
        r = r.json()
        if not r['success']:
            msg = f"Token generation failed: {r['msg']}"
            raise RuntimeError(msg)
        else:
            return r['token']


    def _retrieve_key_client(self, map_name: tuple[str, str, str]
                             ) -> tuple[int, int, int, int] | None:
        """
        Retrieve ID and private map key for given map name from key server.

        :param map_name: Map name (machine, material, tool)
        :return: Tuple of map ID, n value of public key,
            and p and q values of private key
        """
        start = time.monotonic()
        log.debug("Retrieve private key called.")
        log.info("Retrieving private key...")
        j = {'map_name': map_name}
        resp = self.post(f"{self.keyserver}/retrieve_key_client",
                         json=j)
        suc = resp.json()['success']
        self.eval['client_key_retrieval_time'] = time.monotonic()
        log.info( f"Private key retrieval took: {print_time(time.monotonic()-start)}")
        if suc:
            log.debug("Successfully retrieved private key.")
            return resp.json()['id_key']
        else:
            msg = resp.json()['msg']
            raise RuntimeError(f"Failed to retrieve private key: {msg}")
