"""
Test for user database

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""
import logging
import os
import shutil
from time import time
from unittest import TestCase
from unittest.mock import patch, Mock

from flask import Flask

from src.lib import user_database as user_db, config
from src.lib.user import UserType

test_dir = config.DATA_DIR + "test/"


def create_mock_app():
    """Create a low overhead flask app for testing."""
    app = Flask(__name__)
    app.config.from_mapping(
        TESTING=True,
        DATA_DIR=test_dir,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{test_dir}/{config.MAP_DB}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )
    return app


class UserDBTest(TestCase):

    app = create_mock_app()
    username = "username"
    password = "password"
    token = "token"
    t = user_db.Token(value=token)
    tokens = [t]

    @classmethod
    def setUpClass(cls) -> None:
        start = time()
        shutil.rmtree(test_dir, ignore_errors=True)
        os.makedirs(test_dir, exist_ok=True)
        user_db.db.init_app(cls.app)
        cls.app.app_context().push()
        user_db.db.create_all()
        # Add users
        cls.p = user_db.Producer(username=cls.username, password=cls.password)
        user_db.db.session.add(cls.p)
        user_db.db.session.commit()
        # print(f"setUpClass took: {1000 * (time() - start)}  ms")

    def setUp(self) -> None:
        """Clear test directory, remove logging"""
        logging.getLogger().setLevel(logging.ERROR)

    @classmethod
    def tearDownClass(cls) -> None:
        """Remove test directory."""
        shutil.rmtree(test_dir, ignore_errors=True)

    @patch("src.lib.user_database.generate_password_hash",
           return_value="token_hash")
    def test_generate_token(self, m):
        with self.assertRaises(ValueError):
            # User does not exist
            user_db.generate_token(UserType.Producer, "bad")
        t = user_db.generate_token(UserType.Producer, self.username)
        m.assert_called_once_with(t, salt_length=32)

    @patch("src.lib.user_database.check_password_hash", Mock(return_value=True))
    def test_verify_password(self):
        with self.assertRaises(ValueError):
            user_db.verify_password(UserType.Producer, "user", "pwd")
        user_db.verify_password(UserType.Producer, self.username, self.password)

    @patch("src.lib.user_database.check_password_hash")
    def test_verify_token(self, m):
        with self.assertRaises(ValueError):
            # User does not exist
            user_db.verify_token(UserType.Producer, "user", "pwd")
        self.p.tokens = []
        user_db.db.session.commit()
        with self.assertRaises(ValueError):
            # Token is none
            user_db.verify_token(UserType.Producer, self.username, "pwd")
        self.p.tokens = self.tokens
        user_db.db.session.commit()
        m.return_value = False
        self.assertFalse(
            user_db.verify_token(UserType.Producer, self.username, self.token))
        m.return_value = True
        self.assertTrue(
            user_db.verify_token(UserType.Producer, self.username, self.token))
        # Token has been removed
        self.assertEqual([], self.p.tokens)

    def test__generate_token(self):
        token = user_db._generate_token()
        self.assertTrue(isinstance(token, str))
        self.assertEqual(len(token), 86)
        # Test "Randomness"
        l1 = []
        for _ in range(10):
            t = user_db._generate_token()
            self.assertFalse(t in l1)
            l1.append(t)

    @patch("src.lib.user_database.check_password_hash")
    @patch("src.lib.user_database.generate_password_hash")
    def test_update_password(self, gen, m):
        m.return_value = False
        with self.assertRaises(ValueError):
            # Bad Login
            user_db.update_password(UserType.Producer, self.username, "wrong-pwd",
                               "password")
        m.return_value = True
        with self.assertRaises(ValueError):
            # Pwd too short
            user_db.update_password(UserType.Producer, self.username, self.password,
                               "pwd")
        gen.return_value = "new-password-hash"
        # change
        user_db.update_password(UserType.Producer, self.username, self.password,
                           "new-password")
        # Verify
        gen.assert_called_once_with("new-password", salt_length=32)
        self.assertEqual("new-password-hash",
                         user_db.Producer.query.filter_by(
                             username=self.username).first().password)
        # change back
        self.p.password = self.password
        user_db.db.session.commit()

    def test_get_all_users(self):
        res = user_db.get_all_users(UserType.Producer)
        self.assertEqual([self.username], res)

    @patch("src.lib.user_database.generate_password_hash",
           Mock(return_value="password"))
    def test_add_user(self):
        with self.assertRaises(ValueError):
            # Too Short pw
            user_db.add_user(UserType.Producer, "blub", "short")
        with self.assertRaises(ValueError):
            # User exists
            user_db.add_user(UserType.Producer, self.username, self.password)
        self.assertEqual(
            None,
            user_db.Producer.query.filter_by(username="new-user").first())
        user_db.add_user(UserType.Producer, "new-user", "new-password")
        user = user_db.Producer.query.filter_by(username="new-user").first()
        self.assertNotEqual(
            None,
            user)
        user_db.db.session.delete(user)
        user_db.db.session.commit()

    def test_get_user_type(self):
        with self.assertRaises(TypeError):
            user_db.get_user_type("Bad Type")
        self.assertEqual(user_db.Producer, user_db.get_user_type(UserType.Producer))

    def test_get_user(self):
        with self.assertRaises(ValueError):
            user_db.get_user(UserType.Producer, "non-existing")
        self.assertEqual(self.p, user_db.get_user(UserType.Producer, self.username))
