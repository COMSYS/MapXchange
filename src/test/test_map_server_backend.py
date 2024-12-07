"""
Test for mapserver backend

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
from phe import paillier

import src.lib.config as config
import src.lib.map_server_backend as map_server
from src.producer import Record


test_dir = config.DATA_DIR + "test/"
mock_app = Flask(__name__)
mock_app.config.from_mapping(
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{test_dir}/{config.MAP_DB}",
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
class MapServerTest(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        """Create directory for test files."""
        logging.getLogger().setLevel(logging.FATAL)
        shutil.rmtree(test_dir, ignore_errors=True)
        os.makedirs(test_dir, exist_ok=True)
        map_server.db.init_app(mock_app)

    def setUp(self) -> None:
        """Create SQLAlchemy tables for testing."""
        with mock_app.test_request_context():
            map_server.db.create_all()

    def tearDown(self) -> None:
        """Drop SQLAlchemy tables for testing."""
        with mock_app.test_request_context():
            map_server.db.drop_all()

    @classmethod
    def tearDownClass(cls) -> None:
        """Remove directory for test files."""
        shutil.rmtree(test_dir, ignore_errors=True)

    def test_prepare_comparisons(self):
        s = map_server.MapServer(test_dir)
        with mock_app.test_request_context():
            map_server.db.session.add(map_server.Producer(username="provider",
                                                          password="password"))
            provider = map_server.get_user(map_server.UserType.Producer, "provider")
            machine, material, tool = record_1.map_name
            map_key = map_server.MapKey(map_id=1,
                                 machine=machine,
                                 material=material,
                                 tool=tool,
                                 public_key_n=public_key.n,
                                 first_provider=provider)
            map_server.db.session.add(map_key)

            points = []
            offset = 13
            for ap, ae, fz, usage in record_1.points:
                point = map_server.StoredPoint(map=map_key,
                                            ap=ap,
                                            ae=ae,
                                            fz_optimal=public_key.encrypt(
                                                fz+offset).ciphertext(),
                                            provider_optimal=provider,
                                            current_offset=offset)
                map_server.db.session.add(point)
                points.append(point)
            map_server.db.session.commit()
            for point in points:
                self.assertNotIn(provider, point.open_requests)
                self.assertNotIn(provider, point.current_comparators)

            res = s._prepare_comparisons(points, provider)
            res_pt = [(point_id,
                       private_key.decrypt(
                           paillier.EncryptedNumber(public_key, fz_ct)),
                       0, 0)
                      for point_id, fz_ct, _, _ in res]
            expected_res = []
            for p_id in range(10):
                expected_res.append(
                    (p_id+1, record_1.points[p_id][2]+offset, 0, 0))
            self.assertEqual(expected_res, res_pt)
            for point in points:
                self.assertIn(provider, point.open_requests)
                self.assertIn(provider, point.current_comparators)

    def test_store_comparison(self):
        s = map_server.MapServer(test_dir)
        with mock_app.test_request_context():
            map_server.db.session.add(map_server.Producer(username="provider_1",
                                                          password="password"))
            provider_1 = map_server.get_user(map_server.UserType.Producer, "provider_1")
            map_server.db.session.add(map_server.Producer(username="provider_2",
                                                          password="password"))
            provider_2 = map_server.get_user(map_server.UserType.Producer, "provider_2")
            map_server.db.session.add(map_server.Producer(username="provider_3",
                                                          password="password"))
            provider_3 = map_server.get_user(map_server.UserType.Producer, "provider_3")

            machine_1, material_1, tool_1 = record_1.map_name
            map_key =  map_server.MapKey(map_id=1,
                                 machine=machine_1,
                                 material=material_1,
                                 tool=tool_1,
                                 public_key_n=public_key.n,
                                 first_provider=provider_1)
            map_server.db.session.add(map_key)

            ap, ae, fz, usage = record_1.points[0]
            fz_less = fz - 1
            fz_greater = fz + 1
            offset = 13
            point = map_server.StoredPoint(map=map_key,
                                            ap=ap,
                                            ae=ae,
                                            fz_optimal=public_key.encrypt(
                                                fz+offset).ciphertext(),
                                            provider_optimal=provider_1,
                                            fz_pending=public_key.encrypt(
                                                fz_less+offset).ciphertext(),
                                            provider_pending=provider_2,
                                            fz_unknown=public_key.encrypt(
                                                fz_greater+offset).ciphertext(),
                                            provider_unknown=provider_3,
                                            current_offset=offset)
            map_server.db.session.add(point)
            map_server.db.session.commit()

            map_server.db.session.add(map_server.Producer(username="client",
                                                          password="password"))
            client = map_server.get_user(map_server.UserType.Producer, "client")
            comparison = s._prepare_comparisons([point], client)[0]
            _, fz_ct, fz_less_ct, fz_greater_ct = comparison

            with self.assertRaises(ValueError):
                s._store_comparison((point.id, fz_ct, 0), client)
            with self.assertRaises(ValueError):
                s._store_comparison((point.id, 0, fz_greater_ct), client)
            with self.assertRaises(ValueError):
                s._store_comparison((point.id, fz_less_ct, fz_greater_ct), client)
            self.assertEqual(point, s._store_comparison(
                (point.id, fz_ct, fz_greater_ct), client))
            self.assertEqual(None, point.fz_unknown)
            self.assertEqual(None, point.provider_unknown)
            self.assertEqual(client, point.last_comparator)
            self.assertNotIn(client, point.current_comparators)

    @patch("src.lib.map_server_backend.MapServer._prepare_comparisons",
           Mock())
    def test_get_comparisons_provider(self):
        s = map_server.MapServer(test_dir)
        with mock_app.test_request_context():
            map_server.db.session.add(map_server.Producer(username="provider",
                                                          password="password"))
            provider = map_server.get_user(map_server.UserType.Producer, "provider")
            ap_ae = [(ap, ae) for ap, ae, fz, usage in record_1.points]
            s.get_comparisons_provider(1, record_1.map_name, public_key.n, ap_ae, "provider")
            machine, material, tool = record_1.map_name
            map_key = map_server.MapKey.query.filter(
                map_server.MapKey.map_id == 1,
                map_server.MapKey.machine == machine,
                map_server.MapKey.material == material,
                map_server.MapKey.tool == tool).one()
            self.assertEqual(public_key.n, map_key.public_key_n)
            self.assertEqual(provider, map_key.first_provider)

            map_usage = map_server.MapUsage.query.filter(
                map_server.MapUsage.map_id == 1,
                map_server.MapUsage.provider == provider).one()
            self.assertEqual(map_key, map_usage.map)
            self.assertEqual(provider, map_usage.provider)

            for ap, ae in ap_ae:
                point = map_server.StoredPoint.query.filter(
                    map_server.StoredPoint.map_id == 1,
                    map_server.StoredPoint.ap == ap,
                    map_server.StoredPoint.ae == ae).one()
                self.assertEqual(map_key, point.map)

    @patch("src.lib.map_server_backend.MapServer._store_comparison")
    def test_store_records(self, _store_comparison):
        s = map_server.MapServer(test_dir)
        with mock_app.test_request_context():
            map_server.db.session.add(map_server.Producer(username="provider_1",
                                                          password="password"))
            provider_1 = map_server.get_user(map_server.UserType.Producer, "provider_1")
            map_server.db.session.add(map_server.Producer(username="provider_2",
                                                          password="password"))
            provider_2 = map_server.get_user(map_server.UserType.Producer, "provider_2")

            machine, material, tool = record_1.map_name
            map_key = map_server.MapKey(map_id=1,
                                 machine=machine,
                                 material=material,
                                 tool=tool,
                                 public_key_n=public_key.n,
                                 first_provider=provider_1)
            map_server.db.session.add(map_key)

            map_usage = map_server.MapUsage(map=map_key,
                                     provider=provider_2)
            map_server.db.session.add(map_usage)

            ap, ae, fz, usage = (1, 2, 3, 4)
            fz_ct = public_key.encrypt(fz).ciphertext()
            usage_ct = public_key.encrypt(usage).ciphertext()
            usage_ct_double = public_key.encrypt(usage*2).ciphertext()
            offset = 13
            point = map_server.StoredPoint(map=map_key,
                                        ap=ap,
                                        ae=ae,
                                        usage_total=usage_ct,
                                        fz_optimal=fz_ct,
                                        provider_optimal=provider_1,
                                        current_offset=offset)
            map_server.db.session.add(point)
            map_server.db.session.commit()

            point.open_requests.append(provider_2)
            _store_comparison.return_value = point
            s.store_records([(1, 0, 0, fz_ct, usage_ct)], "provider_2")
            self.assertEqual(provider_1, point.provider_optimal)
            self.assertEqual(fz,
                private_key.decrypt(
                    paillier.EncryptedNumber(public_key, point.fz_optimal)))
            self.assertEqual(provider_2, point.provider_unknown)
            self.assertEqual(fz,
                private_key.decrypt(
                    paillier.EncryptedNumber(public_key, point.fz_unknown)) - offset)
            self.assertEqual(
                private_key.decrypt(
                    paillier.EncryptedNumber(public_key, usage_ct_double)),
                private_key.decrypt(
                    paillier.EncryptedNumber(public_key, point.usage_total)))
            self.assertEqual(
                private_key.decrypt(
                    paillier.EncryptedNumber(public_key, usage_ct)),
                private_key.decrypt(
                    paillier.EncryptedNumber(public_key, map_usage.usage_provider)))

    @patch("src.lib.map_server_backend.RetrievalProducer")
    def test_add_to_retrieval_db_producer(self, RetrievalProducer):
        with mock_app.test_request_context():
            map_server.db.session.add(map_server.Producer(username="client",
                                                          password="password"))
            client = map_server.get_user(map_server.UserType.Producer, "client")
            with self.assertRaises(ValueError):
                map_server.MapServer._add_to_retrieval_db_producer(record_1.points, client)
                self.assertEqual(1, RetrievalProducer.call_count)
                expected = {
                    "client": client,
                    "point_count": len(record_1.points)
                }
                self.assertEqual(expected, RetrievalProducer.call_args[1])

    @patch("src.lib.map_server_backend.BillingProducer")
    def test_add_to_billing_db_producer(self, BillingProducer):
        s = map_server.MapServer(test_dir)
        with mock_app.test_request_context():
            map_server.db.session.add(map_server.Producer(username="provider_1",
                                                          password="password"))
            provider_1 = map_server.get_user(map_server.UserType.Producer, "provider_1")
            map_server.db.session.add(map_server.Producer(username="provider_2",
                                                          password="password"))
            provider_2 = map_server.get_user(map_server.UserType.Producer, "provider_2")

            machine_1, material_1, tool_1 = record_1.map_name
            map_key_1 =  map_server.MapKey(map_id=1,
                                 machine=machine_1,
                                 material=material_1,
                                 tool=tool_1,
                                 public_key_n=public_key.n,
                                 first_provider=provider_1)
            map_server.db.session.add(map_key_1)
            machine_2, material_2, tool_2 = record_2.map_name
            map_key_2 =  map_server.MapKey(map_id=2,
                                 machine=machine_2,
                                 material=material_2,
                                 tool=tool_2,
                                 public_key_n=public_key.n,
                                 first_provider=provider_2)
            map_server.db.session.add(map_key_2)

            points = []
            for ap, ae, fz, usage in record_1.points:
                point = map_server.StoredPoint(map=map_key_1,
                                            ap=ap,
                                            ae=ae,
                                            provider_optimal=provider_1)
                map_server.db.session.add(point)
                points.append(point)
            for ap, ae, fz, usage in record_2.points:
                point = map_server.StoredPoint(map=map_key_2,
                                            ap=ap,
                                            ae=ae,
                                            provider_optimal=provider_2)
                map_server.db.session.add(point)
                points.append(point)

            map_server.db.session.add(map_server.Producer(username="client",
                                                          password="password"))
            client = map_server.get_user(map_server.UserType.Producer, "client")
            retrieval =  s._add_to_retrieval_db_producer(points, client)

            with self.assertRaises(ValueError):
                s._add_to_billing_db_producer(points, client, retrieval)
                self.assertEqual(2, BillingProducer.call_count)
                expected = [
                    ({
                        "provider": provider_1,
                        "count_provider": len(record_1.points),
                        "client": client,
                        "retrieval": None
                    },),
                    ({
                        "provider": provider_2,
                        "count_provider": len(record_2.points),
                        "client": client,
                        "retrieval": None
                    },)
                ]
                self.assertEqual(expected, BillingProducer.call_args_list)
