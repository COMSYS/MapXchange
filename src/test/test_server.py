"""
Test for server

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import json
import logging
import shutil
from unittest import TestCase
from unittest.mock import patch

from flask import Flask

from src.lib import server
from src.lib import config
from src.lib.user import UserType

test_dir = config.DATA_DIR + "test/"
producer = "producer"
password = "password"
token = "token"


def mock_verify_pw(user_type, user, pw):
    """Mock method for password check with few overhead (without expensive
    hashing)."""
    return (user == producer) and pw == password


def mock_verify_token(user_type, user, tk):
    """Mock method for password check with few overhead (without expensive
        hashing)."""
    return (user == producer) and tk == token


class ServerTest(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        """Create mock app and remove old test data."""
        logging.getLogger().setLevel(logging.ERROR)
        shutil.rmtree(test_dir, ignore_errors=True)
        cls.app = get_mock_app()
        cls.client = cls.app.test_client()

    def setUp(self) -> None:
        """Enable log-in for testing."""
        self.app.config.update(LOGIN_DISABLED=False)

    def test_disable_login(self):
        with self.app.test_request_context('/'):
            self.app.config.update(LOGIN_DISABLED=True)
            self.assertTrue(server.verify_token("producer", "user", "token"))

    @patch("src.lib.server.user_db")
    def test_verify_token(self, mock_db):
        with self.app.test_request_context('/'):
            mock_db.verify_token.side_effect = TypeError()
            with self.assertRaises(TypeError) as e:
                server.verify_token("wrong", "user", "token")
            mock_db.verify_token.side_effect = ValueError()
            self.assertFalse(server.verify_token(
                UserType.Producer, "non-existing-user", "token"))
            mock_db.verify_password.side_effect = None
            mock_db.verify_token = mock_verify_token
            self.assertFalse(server.verify_token(UserType.Producer, "producer",
                                                  "wrong"))
            self.assertTrue(server.verify_token(UserType.Producer, "producer",
                                                 token))

    @patch("src.lib.server.user_db")
    def test_verify_producer_pw(self, mock_db):
        with self.app.test_request_context('/'):
            mock_db.verify_password.side_effect = ValueError()
            self.assertFalse(server.verify_producer_pw("non-existing-user",
                                                      "wrong"))
            mock_db.verify_password.side_effect = None
            mock_db.verify_password = mock_verify_pw
            self.assertFalse(server.verify_producer_pw("producer", "wrong"))
            self.assertTrue(server.verify_producer_pw("producer", "password"))
            self.app.config.update(LOGIN_DISABLED=True)
            self.assertTrue(server.verify_producer_pw("producer", "wrong"))
            self.assertTrue(server.verify_producer_pw("non-existing-user",
                                                     "wrong"))

    @patch("src.lib.server.user_db")
    def test_gen_token(self, mock_db):
        with self.app.test_request_context('/'):
            # Non existing user
            mock_db.generate_token.side_effect = ValueError(
                'Could not generate token: No user non-existing-user exists.')
            j = json.loads(server.gen_token(UserType.Producer,
                                             "non-existing-user").data)
            self.assertEqual(j['success'], False)
            self.assertEqual(j['msg'], "Could not generate token: No user "
                                       "non-existing-user exists.")

            # Success
            mock_db.generate_token.return_value = "new_token"
            mock_db.generate_token.side_effect = None
            j = json.loads(server.gen_token(UserType.Producer,
                                             "producer").data)
            self.assertEqual(j['success'], True)
            self.assertEqual(j['token'], "new_token")


def get_mock_app() -> Flask:
    """Return a mock flask app with few overhead."""
    app = Flask(__name__)
    app.config.from_mapping(
        TESTING=True,
        DATA_DIR=test_dir,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{test_dir}/{config.MAP_DB}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )
    return app
