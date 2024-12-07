"""
Test for user

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import logging
from unittest import TestCase
from unittest.mock import Mock, patch

import requests
import responses

from src.lib import user
from src.lib.user import KEYSERVER, MAPSERVER, ServerType


class MockUser(user.User):
    """Mock base client to test abstract base class."""
    type = 'mock'


class UserTest(TestCase):
    m: MockUser = None

    @classmethod
    def setUpClass(cls) -> None:
        """Disable logging."""
        logging.getLogger().setLevel(logging.FATAL)

    def setUp(self) -> None:
        self.m = MockUser("testuser")

    def test_init(self):
        m = MockUser("User1")
        self.assertEqual(m.type, "mock")
        self.assertEqual(m.user, "User1")

    def test_set_password(self):
        m = MockUser("client")
        self.assertIsNone(m.password)
        m.set_password("password")
        self.assertEqual(m.password, "password")

    @responses.activate
    def test_get_token_success(self):
        urlA = f"{KEYSERVER}/mock/gen_token"
        urlB = f"{MAPSERVER}/mock/gen_token"
        j = {
            'success': True,
            'token': 'XIu2a9SDGURRTzQnJdDg19Ii_CS7wy810s3_Lrx-TY7Wvh2Hf0U4xLH'
                     'NwnY_byYJ71II3kfUXpSZHOqAxA3zrw'
        }
        responses.add(responses.GET, urlA, json=j, status=200)
        responses.add(responses.GET, urlB, json=j, status=200)

        # Success keyserver
        self.m.set_password("password")
        res = self.m.get_token(ServerType.KeyServer)
        self.assertEqual(res, j['token'])

        # Success mapserver
        self.m.set_password("password")
        res = self.m.get_token(ServerType.MapServer)
        self.assertEqual(res, j['token'])

    @responses.activate
    def test_get_token_fail(self):
        with self.assertRaises(ValueError):
            # no password defined
            self.m.get_token(ServerType.KeyServer)
        self.m.set_password("password")
        # Bad server type
        with self.assertRaises(ValueError):
            self.m.get_token("Bad-type")
        # Server Error
        url = f"{KEYSERVER}/mock/gen_token"
        j = {
            'success': False,
            'msg': "Not enough entropy."
        }
        responses.add(responses.GET, url, json=j, status=200)
        with self.assertRaises(RuntimeError):
            self.m.get_token(ServerType.KeyServer)

    @responses.activate
    @patch("src.lib.user.User.get_auth_data",
           Mock(return_value=("a", "b")))
    def test_get(self):
        url = "http://url"
        body = b"Test"
        auth = ("user", "password")
        method = responses.GET
        # Success via 200
        responses.add(method, url, body, status=200)
        res = self.m.get(url)  # Without auth
        self.assertEqual(body, res.content)
        # Success via 202
        responses.replace(method, url, body, status=202)
        res = self.m.get(url, auth)
        self.assertEqual(body, res.content)
        # Authentication failed - 401
        responses.replace(method, url, body, status=401)
        with self.assertRaises(RuntimeError) as e:
            self.m.get(url, auth)
        self.assertIn("Authentication failed", str(e.exception))
        # Internal Server Error - 500
        responses.replace(method, url, body, status=500)
        with self.assertRaises(requests.exceptions.HTTPError):
            self.m.get(url, auth)

    @responses.activate
    @patch("src.lib.user.User.get_auth_data",
           Mock(return_value=("a", "b")))
    def test_post(self):
        url = "http://url"
        body = b"Test"
        auth = ("user", "password")
        json = {}
        method = responses.POST
        # Success via 200
        responses.add(method, url, body, status=200)
        res = self.m.post(url, json)  # without auth
        self.assertEqual(body, res.content)
        # success via 202
        responses.replace(method, url, body, status=202)
        res = self.m.post(url, json, auth)
        self.assertEqual(body, res.content)
        # Authentication failed - 401
        responses.replace(method, url, body, status=401)
        with self.assertRaises(RuntimeError) as e:
            self.m.post(url, json, auth)
        self.assertIn("Authentication failed", str(e.exception))
        # Internal Server Error - 500
        responses.replace(method, url, body, status=500)
        with self.assertRaises(requests.exceptions.HTTPError):
            self.m.post(url, json, auth)

    @patch("src.lib.user.User.get_token",
           Mock(return_value='token'))
    def test_get_auth_data(self):
        with self.assertRaises(ValueError):
            self.m.get_auth_data("bad-url")
        self.assertEqual(
            (self.m.user, "token"),
            self.m.get_auth_data(KEYSERVER + "/something")
        )
        self.assertEqual(
            (self.m.user, "token"),
            self.m.get_auth_data(MAPSERVER + "/something")
        )

    @patch("src.lib.user.User.post")
    def test_retrieve_key_client_success(self, post):
        url = f"{KEYSERVER}/mock/retrieve_key_client"
        j = {
            'success': True,
            'id_key': (1, 2, 3, 4)
        }
        post.return_value.json.return_value = j
        res = self.m._retrieve_key_client(('5rLhPSFu', 'hardened steel', 'zJcgKqGI'))
        self.assertEqual(res, j['id_key'])
        post.assert_called_once_with(
            url, json={'map_name': ('5rLhPSFu', 'hardened steel', 'zJcgKqGI')})

    @patch("src.lib.user.User.post")
    def test_retrieve_key_client_fail(self, post):
        url = f"{KEYSERVER}/mock/retrieve_key_client"
        j = {
            'success': False,
            'msg': "No key available for given map name"
        }
        post.return_value.json.return_value = j
        with self.assertRaises(RuntimeError) as cm:
            self.m._retrieve_key_client(('5rLhPSFu', 'hardened steel', 'zJcgKqGI'))
        self.assertIn("No key available for given map name", str(cm.exception))
        post.assert_called_once_with(
            url, json={'map_name': ('5rLhPSFu', 'hardened steel', 'zJcgKqGI')})
