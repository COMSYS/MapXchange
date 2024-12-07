"""
Test for producer

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import argparse
import logging
import os
import shutil
from unittest import TestCase
from unittest.mock import patch

from phe import paillier

from src import producer
from src.lib import config
from src.lib.user import UserType


public_key, private_key = paillier.generate_paillier_keypair(n_length=2048)


class ProducerTest(TestCase):
    test_dir = config.DATA_DIR + "test/"
    p = producer.Producer("userA")

    @classmethod
    def setUpClass(cls) -> None:
        """Create directory for testing."""
        logging.getLogger().setLevel(logging.FATAL)
        shutil.rmtree(cls.test_dir, ignore_errors=True)
        os.makedirs(cls.test_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        """Remove directory for testing."""
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    @patch("src.lib.user.User.post")
    def test_retrieve_key_provider_success(self, m):
        url = (f"https://{config.KEY_HOSTNAME}:"
               f"{config.KEY_API_PORT}/"
               f"{UserType.Producer}/retrieve_key_provider")
        j = {
            'success': True,
            'id_key': (1, 2, 3, 4)
        }
        m.return_value.json.return_value = j
        res = self.p._retrieve_key_provider(
            ('5rLhPSFu', 'hardened steel', 'zJcgKqGI'), ('end mill', 4))
        self.assertEqual(res, j['id_key'])
        m.assert_called_once_with(
            url, json={
                'map_name': ('5rLhPSFu', 'hardened steel', 'zJcgKqGI'),
                'tool_properties': ('end mill', 4)})

    def test_perform_comparisons(self):
        ct_1 = public_key.encrypt(1).ciphertext()
        ct_2 = public_key.encrypt(2).ciphertext()
        ct_3a = public_key.encrypt(3).ciphertext()
        ct_3b = public_key.encrypt(3).ciphertext()
        ct_4 = public_key.encrypt(4).ciphertext()
        comparisons = []
        comparisons.append((1, ct_2, ct_3a, ct_4))
        comparisons.append((2, ct_3a, ct_3b, ct_2))
        comparisons.append((3, ct_1, ct_2, None))
        comparisons.append((4, ct_1, None, ct_2))
        comparisons.append((5, ct_1, None, None))
        res = self.p._perform_comparisons(comparisons, private_key)
        expected_res = []
        expected_res.append((1, ct_3a, ct_4))
        expected_res.append((2, ct_3a, ct_3a))
        expected_res.append((3, ct_2, None))
        expected_res.append((4, None, ct_2))
        expected_res.append((5, None, None))
        self.assertEqual(expected_res, res)

    def test_parser(self):
        # Just syntax errors
        p = producer.get_producer_parser()
        self.assertTrue(isinstance(p, argparse.ArgumentParser))
