"""
Test for keyserver backend

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import atexit
import logging
import os
import shutil
from unittest import TestCase
from unittest.mock import Mock, patch

from flask import Flask
from phe import paillier, PaillierPublicKey, PaillierPrivateKey

import src.lib.config as config
import src.lib.key_server_backend as key_server
from src.producer import Record


logging.getLogger(config.KEY_LOGNAME).setLevel(logging.ERROR)
test_dir = config.DATA_DIR + "test/"
mock_app = Flask(__name__)
mock_app.config.from_mapping(
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{test_dir}/{config.KEY_DB}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)
atexit.register(shutil.rmtree, test_dir, True)

record_1 = Record(('5rLhPSFu', 'hardened steel', 'zJcgKqGI'),
                  ('end mill', 4),
                  [(261, 4, 3412, 6),
                   (35, 28, 24276, 7),
                   (62, 199, 11931, 2),
                   (106, 160, 28188, 4),
                   (173, 227, 29963, 0),
                   (61, 161, 8662, 8),
                   (167, 296, 17988, 4),
                   (159, 86, 8188, 3),
                   (226, 232, 11521, 8),
                   (47, 288, 27166, 8)])

record_2 = Record(('tqExkPZC', 'non-ferrous metal', 'et7TNK8X'),
                  ('ball mill', 4),
                  [(40, 80, 1409, 3),
                   (175, 274, 27695, 4),
                   (85, 155, 13101, 9),
                   (173, 189, 20345, 6),
                   (258, 83, 17569, 6),
                   (184, 106, 5008, 7),
                   (81, 47, 3981, 0),
                   (111, 109, 24480, 4),
                   (84, 104, 15288, 7),
                   (280, 237, 13259, 5)])

public_key, private_key = paillier.generate_paillier_keypair(n_length=2048)

@patch("src.lib.config.DATA_DIR", test_dir)
class TestKeyServer(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        """Create directory for test files."""
        logging.getLogger().setLevel(logging.FATAL)
        shutil.rmtree(test_dir, ignore_errors=True)
        os.makedirs(test_dir, exist_ok=True)
        key_server.db.init_app(mock_app)

    def setUp(self) -> None:
        """Create SQLAlchemy tables for testing."""
        with mock_app.test_request_context():
            key_server.db.create_all()

    def tearDown(self) -> None:
        """Drop SQLAlchemy tables for testing."""
        with mock_app.test_request_context():
            key_server.db.drop_all()

    @classmethod
    def tearDownClass(cls) -> None:
        """Remove directory for test files."""
        shutil.rmtree(test_dir, ignore_errors=True)

    def test_gen_key(self):
        with self.assertRaises(ValueError):
            key_server.KeyServer._gen_key(config.KEY_LEN-1)
        public_key, private_key = key_server.KeyServer._gen_key(config.KEY_LEN)
        self.assertTrue(isinstance(public_key, PaillierPublicKey))
        self.assertTrue(isinstance(private_key, PaillierPrivateKey))

    @patch("src.lib.key_server_backend.KeyServer._gen_key",
           Mock(return_value=(public_key, private_key)))
    def test_get_key_provider(self):
        s = key_server.KeyServer(test_dir)
        with mock_app.test_request_context():
            key_server.db.session.add(key_server.Producer(username="provider",
                                                          password="password"))
            res = s.get_key_provider(
                record_1.map_name, record_1.tool_properties, "provider")
            expected_res = (1, public_key.n, private_key.p, private_key.q)
            self.assertEqual(expected_res, res)

    @patch("src.lib.key_server_backend.KeyServer._gen_key",
           Mock(return_value=(public_key, private_key)))
    def test_get_key(self):
        s = key_server.KeyServer(test_dir)
        with mock_app.test_request_context():
            key_server.db.session.add(key_server.Producer(username="provider",
                                                          password="password"))
            s.get_key_provider(record_1.map_name, record_1.tool_properties, "provider")
            self.assertEqual(1, s._get_key(record_1.map_name).map_id)
            self.assertEqual(None, s._get_key(record_2.map_name))

    @patch("src.lib.key_server_backend.KeyServer._gen_key",
           Mock(return_value=(public_key, private_key)))
    def test_get_key_client(self):
        s = key_server.KeyServer(test_dir)
        with mock_app.test_request_context():
            key_server.db.session.add(key_server.Producer(username="provider",
                                                          password="password"))
            s.get_key_provider(record_1.map_name, record_1.tool_properties, "provider")

            key_server.db.session.add(key_server.Producer(username="client",
                                                          password="password"))
            expected_res = (1, public_key.n, private_key.p, private_key.q)
            self.assertEqual(expected_res, s.get_key_client_producer(record_1.map_name, "client"))
            with self.assertRaises(ValueError):
                s.get_key_client_producer(record_2.map_name, "client")

    @patch("src.lib.key_server_backend.KeyServer._gen_key",
           Mock(return_value=(public_key, private_key)))
    def test_get_map_ids(self):
        s = key_server.KeyServer(test_dir)
        with mock_app.test_request_context():
            key_server.db.session.add(key_server.Producer(username="client",
                                                          password="password"))
            with self.assertRaises(ValueError):
                s.get_map_ids(record_1.map_name[:2], record_1.tool_properties, [], "client")
            key_server.db.session.add(key_server.Producer(username="provider",
                                                          password="password"))
            s.get_key_provider(record_1.map_name, record_1.tool_properties, "provider")
            expected_res = [(1, public_key.n, private_key.p, private_key.q)]
            self.assertEqual(expected_res, s.get_map_ids(record_1.map_name[:2],
                                                         record_1.tool_properties,
                                                         [], "client"))
            with self.assertRaises(ValueError):
                s.get_map_ids(record_1.map_name[:2], record_1.tool_properties,
                            [record_1.map_name[2]], "client")
