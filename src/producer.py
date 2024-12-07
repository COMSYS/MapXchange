#!/usr/bin/env python3
"""
Client application for producers

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import argparse
import logging
import pickle
import sys
import time

from phe import paillier
from memory_profiler import memory_usage

sys.path.append(".")
from src.lib import config
from src.lib.helpers import Record, parse_record, print_time, plot_ap_ae_fz
from src.lib.logging import configure_root_logger
from src.lib.user import User, UserType


configure_root_logger(logging.INFO, config.LOG_DIR + "producer.log")
log = logging.getLogger()


class Producer(User):
    """Producer that buys milling tools"""

    type = UserType.Producer

    def _retrieve_key_provider(self, map_name: tuple[str, str, str],
                               tool_properties: tuple[str, int]
                               ) -> tuple[int, int,
                                          paillier.PaillierPrivateKey]:
        """
        Retrieve ID and public map key for given map name from key server.
        
        :param map_name: Map name (machine, material, tool)
        :param tool_properties: Tool properties (type, diameter)
        :return: Tuple of map ID, n value of public key,
            and p and q values private key
        """
        start = time.monotonic()
        log.debug("Retrieve public key called.")
        log.info("Retrieving public key...")
        j = {
            'map_name': map_name,
            'tool_properties': tool_properties
            }
        resp = self.post(f"{self.keyserver}/retrieve_key_provider",
                         json=j)
        suc = resp.json()['success']
        self.eval['provider_key_retrieval_time'] = time.monotonic()
        log.info( f"Public key retrieval took: {print_time(time.monotonic()-start)}")
        if suc:
            log.debug("Successfully retrieved public key.")
            return resp.json()['id_key']
        else:
            msg = resp.json()['msg']
            raise RuntimeError(f"Failed to retrieve public key: {msg}")

    def _request_comparisons_client(self, map_id: int, ap_ae: list[tuple[int, int]]
                                    ) -> list[tuple[int, int, int, int]]:
        """
        Request comparisons for retrieval.

        :param map_id: Map ID
        :param ap_ae: List of cutting depth/width [(ap, ae)]
        :return: List of tuples containing fz values for each relevant
            point (point_id, fz_optimal, fz_pending, fz_unknown)
        """
        start = time.monotonic()
        log.debug("Request comparisons client called.")
        log.info("Requesting comparisons...")
        j = {
            'map_id': map_id,
            'ap_ae': ap_ae
            }
        resp = self.post(f"{self.mapserver}/request_comparisons_client",
                         json=j)
        suc = resp.json()['success']
        self.eval['comparison_request_time'] = time.monotonic()
        log.info( f"Comparison request took: {print_time(time.monotonic()-start)}")
        if suc:
            log.debug("Successfully requested comparisons.")
            return resp.json()['comparisons']
        else:
            msg = resp.json()['msg']
            raise RuntimeError(f"Failed to request comparisons: {msg}")

    def _request_comparisons_provider(self, map_id: int, map_name: tuple[str, str, str],
                                      n: int, points: list[tuple[int, int, int, int]]
                                      ) -> list[tuple[int, int, int, int]]:
        """
        Request comparisons for provision.

        :param map_id: Map ID
        :param map_name: Map name (machine, material, tool)
        :param n: n value of public key
        :param points: List of points
        :return: List of tuples containing fz values for each relevant
            point [(point_id, fz_optimal, fz_pending, fz_unknown)]
        """
        if any(not isinstance(value, int) or value < 0 for point in points for value in point):
            raise ValueError
        ap_ae = [(ap, ae) for ap, ae, fz, usage in points]

        start = time.monotonic()
        log.debug("Request comparisons provider called.")
        log.info("Requesting comparisons...")
        j = {
            'map_id': map_id,
            'map_name': map_name,
            'n': n,
            'ap_ae': ap_ae
            }
        resp = self.post(f"{self.mapserver}/request_comparisons_provider",
                         json=j)
        suc = resp.json()['success']
        self.eval['comparison_request_time'] = time.monotonic()
        log.info( f"Comparison request took: {print_time(time.monotonic()-start)}")
        if suc:
            log.debug("Successfully requested comparisons.")
            return resp.json()['comparisons']
        else:
            msg = resp.json()['msg']
            raise RuntimeError(f"Failed to request comparisons: {msg}")

    def _perform_comparisons(self, comparisons: list[tuple[int, int, int, int]],
                             private_key: paillier.PaillierPrivateKey
                             ) -> list[tuple[int, int | None, int | None]]:
        """
        Perform comparisons.
        
        :param comparisons: List of tuples containing fz values for requested points
            [(point_id, fz_optimal, fz_pending, fz_unknown)]
        :param private_key: Private map key
        :return: List of comparison results by point
            [(point_id, result_optimal_pending, result_optimal_unknown)]
        """
        start = time.monotonic()
        log.debug("Perform comparisons called.")
        log.info("Performing comparisons...")

        public_key = private_key.public_key
        comparison_results = []
        for comparison in comparisons:
            point_id, fz_optimal_ct, fz_pending_ct, fz_unknown_ct = comparison
            result_optimal_pending = None
            result_optimal_unknown = None

            if fz_optimal_ct: # only ever False for provider
                fz_optimal = paillier.EncryptedNumber(public_key, fz_optimal_ct)
                fz_optimal_pt = private_key.decrypt(fz_optimal)

            if fz_pending_ct:
                fz_pending = paillier.EncryptedNumber(public_key, fz_pending_ct)
                fz_pending_pt = private_key.decrypt(fz_pending)
                if fz_optimal_pt < fz_pending_pt:
                    result_optimal_pending = fz_pending_ct
                else:
                    result_optimal_pending = fz_optimal_ct

            if fz_unknown_ct:
                fz_unknown = paillier.EncryptedNumber(public_key, fz_unknown_ct)
                fz_unknown_pt = private_key.decrypt(fz_unknown)
                if fz_optimal_pt < fz_unknown_pt:
                    result_optimal_unknown = fz_unknown_ct
                else:
                    result_optimal_unknown = fz_optimal_ct

            comparison_results.append(
                (point_id, result_optimal_pending, result_optimal_unknown))

        self.eval['comparison_time'] = time.monotonic()
        log.info( f"Comparisons took: {print_time(time.monotonic()-start)}")
        return comparison_results

    def _perform_comparisons_provider(self, comparisons: list[tuple[int, int, int, int]],
                                      private_key: paillier.PaillierPrivateKey,
                                      points: list[tuple[int, int, int, int]]
                                      ) -> list[tuple[int, int, int, int, int]]:
        """
        Perform comparisons and extend results with values to be provided.

        :param comparisons: List of tuples containing fz values for requested points
            [(point_id, fz_optimal, fz_pending, fz_unknown)]
        :param private_key: Private map key
        :return: List of comparison results, extended with values to be provided
            [(point_id, result_optimal_pending, result_optimal_unknown, fz, usage)]
        """
        comparison_results = self._perform_comparisons(comparisons, private_key)
        public_key = private_key.public_key

        start = time.monotonic()
        log.debug("Perform comparisons provider called.")
        log.info("Adding encrypted values to comparison results...")
        encrypted_values = [(public_key.encrypt(fz).ciphertext(),
                             public_key.encrypt(usage).ciphertext())
                            for ap, ae, fz, usage in points]
        self.eval['encryption_time'] = time.monotonic()
        log.info( f"Encryption took: {print_time(time.monotonic()-start)}")
        return [tuple(results + values) for results, values in
                zip(comparison_results, encrypted_values)]

    def _retrieve_points(self, comparison_results: list[tuple[int, int, int]]
                         )-> list[tuple[int, int, int, int]]:
        """
        Retrieve (encrypted) specified points for given map from map server.
        
        :param comparison_results: List of comparison results by point
            [(point_id, result_optimal_pending, result_optimal_unknown)]
        :return: List of retrieved (encrypted) points
            [(ap, ae, fz_ct, usage_ct)]
        """
        start = time.monotonic()
        log.debug("Retrieve points called.")
        log.info("Retrieving points...")
        j = {'comparison_results': comparison_results}
        resp = self.post(f"{self.mapserver}/retrieve_points",
                         json=j)
        suc = resp.json()['success']
        self.eval['point_retrieval_time'] = time.monotonic()
        log.info( f"Point retrieval took: {print_time(time.monotonic()-start)}")
        if suc:
            log.debug("Successfully retrieved points.")
            return resp.json()['points']
        else:
            msg = resp.json()['msg']
            raise RuntimeError(f"Failed to retrieve points: {msg}")

    def _retrieve_points_plaintext(self, map_id: int, ap_ae: list[tuple[int, int]]
                                   )-> list[tuple[int, int, int, int]]:
        """
        Retrieve (unencrypted) specified points for given map from map server.
        
        :param map_id: Map ID
        :param ap_ae: List of cutting depth/width [(ap, ae)]
        :return: List of retrieved points [(ap, ae, fz, usage)]
        """
        if config.USE_PAILLIER and config.VALID:
            raise RuntimeError("Plaintext retrieval not allowed for secure scheme!")
        start = time.monotonic()
        log.debug("Retrieve points plaintext called.")
        log.info("Retrieving plaintext points...")
        j = {
            'map_id': map_id,
            'ap_ae': ap_ae
            }
        resp = self.post(f"{self.mapserver}/retrieve_points_plaintext",
                         json=j)
        suc = resp.json()['success']
        self.eval['plaintext_point_retrieval_time'] = time.monotonic()
        log.info( f"Plaintext point retrieval took: {print_time(time.monotonic()-start)}")
        if suc:
            log.debug("Successfully retrieved plaintext points.")
            return resp.json()['points']
        else:
            msg = resp.json()['msg']
            raise RuntimeError(f"Failed to retrieve plaintext points: {msg}")

    def _decrypt_points(self, private_key: paillier.PaillierPrivateKey,
                        encrypted_points: list[tuple[int, int, int, int]]
                        ) -> list[tuple[int, int, int, int]]:
        """
        Decrypt feed per tooth and usage values, return plaintext points.

        :param private_key: Private map key
        :param encrypted_points: List of encrypted points
            [(ap, ae, fz_ct, usage_ct)]
        :return: List of decrypted points [(ap, ae, fz, usage)]
        """
        start = time.monotonic()
        log.debug("Decrypt points called.")
        log.info("Decrypting points...")

        public_key = private_key.public_key
        points = [(ap, ae,
                   private_key.decrypt(paillier.EncryptedNumber(public_key, fz_ct)),
                   private_key.decrypt(paillier.EncryptedNumber(public_key, usage_ct)))
                   for ap, ae, fz_ct, usage_ct in encrypted_points]

        self.eval['point_decryption_time'] = time.monotonic()
        log.info( f"Point decryption took: {print_time(time.monotonic()-start)}")
        return points


    def regular_query(self, map_name: tuple[str, str, str],
                      ap_ae: list[tuple[int, int]]
                      ) -> list[tuple[int, int, int, int]]:
        """
        Perform regular query, retrieving points from map server.

        :param map_name: Map name (machine, material, tool)
        :param ap_ae: List of tuples of cutting depth/width values [(ap, ae)]
        :return: List of retrieved points [(ap, ae, fz, usage)]
        """
        self.eval['start_time'] = time.monotonic()
        try:
            log.info(f"Regular query: Retrieve up to {len(ap_ae)} points.")
            map_id, n, p, q = self._retrieve_key_client(map_name)
            if config.USE_PAILLIER:
                private_key = paillier.PaillierPrivateKey(paillier.PaillierPublicKey(n), p, q)
                if config.VALID:
                    comparisons = self._request_comparisons_client(map_id, ap_ae)
                    comparison_results = self._perform_comparisons(comparisons, private_key)
                    encrypted_points = self._retrieve_points(comparison_results)
                else:
                    encrypted_points = self._retrieve_points_plaintext(map_id, ap_ae)
                points = self._decrypt_points(private_key, encrypted_points)
            else:
                points = self._retrieve_points_plaintext(map_id, ap_ae)
            log.info(f"Retrieved {len(points)} points.")
            return points
        except Exception as e:
            log.exception(str(e))
            raise e

    def _retrieve_map_ids(self, map_name_prefix: tuple[str, str],
                          tool_properties: tuple[str, int],
                          excluded_tools: list[str]
                          ) -> tuple[list[int], list[tuple[int, int, int]]]:
        """
        Retrieve map IDs and private keys for given tool properties from key server.

        :param map_name_prefix: Map name without tool (machine, material)
        :param tool_properties: Tool properties (type, diameter)
        :param excluded_tools: Tools not to retrieve map ID for
        :return: List of tuples of retrieved map IDs and private keys
            [(map_id, public_key_n, private_key_p, private_key_q)]
        """
        start = time.monotonic()
        log.debug("Retrieve map IDs called.")
        log.info("Retrieving map IDs...")
        j = {
            'map_name_prefix': map_name_prefix,
            'tool_properties': tool_properties,
            'excluded_tools': excluded_tools
            }
        resp = self.post(f"{self.keyserver}/retrieve_map_ids",
                         json=j)
        suc = resp.json()['success']
        self.eval['ids_retrieval_time'] = time.monotonic()
        log.info( f"Map IDs retrieval took: {print_time(time.monotonic()-start)}")
        if suc:
            log.debug("Successfully retrieved map ids.")
            return resp.json()['ids_keys']
        else:
            msg = resp.json()['msg']
            raise RuntimeError(f"Failed to retrieve map ids: {msg}")

    def _retrieve_previews(self, map_ids: list[int]
                           ) -> list[tuple[int, tuple[int, int, int, int]]]:
        """
        Retrieve (encrypted) map previews for given map IDs from map server.

        :param map_ids: Map IDs
        :return: List of retrieved points with shifted fz values
            [(ap, ae, shifted_fz_ct, usage_ct)]
        """
        start = time.monotonic()
        log.debug("Retrieve previews called.")
        log.info("Retrieving previews...")
        j = {'map_ids': map_ids}
        resp = self.post(f"{self.mapserver}/retrieve_previews",
                         json=j)
        suc = resp.json()['success']
        self.eval['preview_retrieval_time'] = time.monotonic()
        log.info( f"Preview retrieval took: {print_time(time.monotonic()-start)}")
        if suc:
            log.debug("Successfully retrieved previews.")
            return resp.json()['previews']
        else:
            msg = resp.json()['msg']
            raise RuntimeError(f"Failed to retrieve previews: {msg}")

    def _retrieve_previews_plaintext(self, map_ids: list[int]
                                     ) -> list[tuple[int, tuple[int, int, int, int]]]:
        """
        Retrieve (unencrypted) map previews for given map IDs from map server.

        :param map_ids: Map IDs
        :return: List of retrieved points with shifted fz values
            [(ap, ae, shifted_fz, usage)]
        """
        if config.USE_PAILLIER:
            raise RuntimeError("Plaintext retrieval not allowed for secure scheme!")
        start = time.monotonic()
        log.debug("Retrieve previews plaintext called.")
        log.info("Retrieving plaintext previews...")
        j = {'map_ids': map_ids}
        resp = self.post(f"{self.mapserver}/retrieve_previews_plaintext",
                         json=j)
        suc = resp.json()['success']
        self.eval['plaintext_preview_retrieval_time'] = time.monotonic()
        log.info( f"Plaintext preview retrieval took: {print_time(time.monotonic()-start)}")
        if suc:
            log.debug("Successfully retrieved plaintext previews.")
            return resp.json()['previews']
        else:
            msg = resp.json()['msg']
            raise RuntimeError(f"Failed to retrieve plaintext previews: {msg}")

    def _decrypt_previews(self, map_id_to_keys: dict,
                          encrypted_previews:
                          list[tuple[int, list[tuple[int, int, int, int]]]]
                          ) -> list[tuple[int, list[tuple[int, int, int, int]]]]:
        """
        Decrypt shifted feed per tooth and usage values, return plaintext previews.

        :param map_id_to_keys: Dict mapping map ID to private key
        :param encrypted_previews: Encrypted previews, i.e., tuples of
            map ID and list of encrypted points with shifted fz value
            [(ap, ae, shifted_fz_ct, usage_ct)]
        :return: Decrypted previews, i.e, tuples of map ID and
            list of points with shifted fz value
            [(ap, ae, shifted_fz, usage)]
        """
        start = time.monotonic()
        log.debug("Decrypt previews called.")
        log.info("Decrypting previews...")

        previews = []
        for map_id, encrypted_preview in encrypted_previews:
            private_key = map_id_to_keys[map_id]
            public_key = private_key.public_key
            preview = [(ap, ae,
                        private_key.decrypt(
                            paillier.EncryptedNumber(public_key, shifted_fz_ct)),
                        private_key.decrypt(
                            paillier.EncryptedNumber(public_key, usage_ct)))
                        for ap, ae, shifted_fz_ct, usage_ct in encrypted_preview]
            previews.append((map_id, preview))

        self.eval['preview_decryption_time'] = time.monotonic()
        log.info( f"Preview decryption took: {print_time(time.monotonic()-start)}")
        return previews

    def reverse_query(self, map_name_prefix: tuple[str, str],
                      tool_properties: tuple[str, int],
                      excluded_tools: list[str]
                      ) -> list[tuple[int,
                                      list[tuple[int, int, int, int]]]]:
        """
        Perform reverse query, retrieving previews from map server.

        :param map_name_prefix: Map name without tool (machine, material)
        :param tool_properties: Tool properties (type, diameter)
        :param excluded_tools: Tools not to retrieve map ID for
        :return: List of retrieved previews by map key ID:
            [
                (map_id_1, [(ap, ae, shifted_fz, usage)]),
                (map_id_2, [(ap, ae, shifted_fz, usage)]),
                ...
            ]
        """
        self.eval['start_time'] = time.monotonic()
        try:
            log.info(f"Reverse query: Retrieve all but {len(excluded_tools)} map previews.")
            ids_keys = self._retrieve_map_ids(map_name_prefix, tool_properties, excluded_tools)

            map_id_to_keys = dict((map_id, paillier.PaillierPrivateKey(
                paillier.PaillierPublicKey(n), p, q))
                for map_id, n, p, q in ids_keys)

            if config.USE_PAILLIER:
                encrypted_previews = self._retrieve_previews(list(map_id_to_keys.keys()))
                previews = self._decrypt_previews(map_id_to_keys, encrypted_previews)
            else:
                previews = self._retrieve_previews_plaintext(list(map_id_to_keys.keys()))
            log.info(f"Retrieved {len(previews)} map previews.")
            return previews
        except Exception as e:
            log.exception(str(e))
            raise e

    def _retrieve_preview_info(self, map_id: int) -> tuple[int, str]:
        """
        Retrieve offset used in map preview and tool name from map server.

        :param map_id: Map ID
        :return: Tuple of offset used in preview and tool name
        """
        start = time.monotonic()
        log.debug("Retrieve preview info called.")
        log.info("Retrieving preview info...")
        j = {'map_id': map_id}
        resp = self.post(f"{self.keyserver}/retrieve_preview_info",
                         json=j)
        suc = resp.json()['success']
        self.eval['preview_info_retrieval_time'] = time.monotonic()
        log.info( f"Preview info retrieval took: {print_time(time.monotonic()-start)}")
        if suc:
            log.debug("Successfully retrieved preview info.")
            return resp.json()['preview_info']
        else:
            msg = resp.json()['msg']
            raise RuntimeError(f"Failed to retrieve preview info: {msg}")

    def reverse_query_choice(self, map_id: int) -> tuple[int, str]:
        """
        Choose preview (from prior reverse query), retrieving preview info.

        :param map_id: Map ID
        :return: Tuple of offset used in preview and tool name
        """
        self.eval['start_time'] = time.monotonic()
        try:
            log.info(f"Reverse query choice: Retrieve preview info for map ID {map_id}.")
            offset, tool = self._retrieve_preview_info(map_id)
            log.info(f"Retrieved preview info for map ID {map_id}.")
            return (offset, tool)
        except Exception as e:
            log.exception(str(e))
            raise e

    def _provide_records(self, comparison_results_with_values:
                         list[tuple[int, int, int, int, int]]) -> None:
        """
        Provide optimal feed per tooth points and usage data to map server,
        alongside comparison results.

        :param comparison_results_with_values: List of comparison results,
            extended with values to be provided
            [(point_id, result_optimal_pending, result_optimal_unknown, fz, usage)]
        """
        start = time.monotonic()
        log.debug("Provide records called.")
        log.info("Providing records...")
        j = {'comparison_results_with_values': comparison_results_with_values}
        r = self.post(f"{self.mapserver}/provide_records", json=j)
        suc = r.json()['success']
        self.eval['provision_time'] = time.monotonic()
        log.info( f"Provision took: {print_time(time.monotonic()-start)}")
        if suc:
            log.debug("Successfully provided records.")
        else:
            msg = r.json()['msg']
            raise RuntimeError(f"Failed to provide records: {msg}")

    def _provide_records_plaintext(self, map_id: int, map_name: tuple[str, str, str],
                                   points: list[tuple[int, int, int, int]], n: int = 0) -> None:
        """
        Provide optimal feed per tooth points and usage data to map server,
        as plaintext.

        :param map_id: Map ID
        :param map_name: Map name
        :param points: List of points to be provided [(ap, ae, fz, usage)]
        :param n: n value of public key (for evaluation without validation)
        """
        if config.USE_PAILLIER and config.VALID:
            raise RuntimeError("Plaintext provision not allowed for secure scheme!")
        start = time.monotonic()
        log.debug("Provide records plaintext called.")
        log.info("Providing plaintext records...")
        j = {'map_id': map_id,
             'map_name': map_name,
             'points': points,
             'n': n}
        r = self.post(f"{self.mapserver}/provide_records_plaintext", json=j)
        suc = r.json()['success']
        self.eval['plaintext_provision_time'] = time.monotonic()
        log.info( f"Plaintext provision took: {print_time(time.monotonic()-start)}")
        if suc:
            log.debug("Successfully provided plaintext records.")
        else:
            msg = r.json()['msg']
            raise RuntimeError(f"Failed to provide plaintext records: {msg}")

    def full_provide(self, records: list[Record]) -> None:
        """
        Perform full provision for given map to map server.

        :param records: List of records [Record], each of which is
            tuple of map name (machine, material, tool),
            tool properties (tool type, tool diameter),
            and list of points [(ap, ae, fz, usage)]
        """
        self.eval['start_time'] = time.monotonic()
        aggregated_records = {}
        for record in records:
            map_name = record.map_name
            if record.map_name in aggregated_records:
                aggregated_records[map_name].points.extend(record.points)
            else:
                aggregated_records[map_name] = record

        try:
            log.info(f"Provide up to {len(records)} records.")
            for record in aggregated_records.values():
                map_id, n, p, q = self._retrieve_key_provider(
                    record.map_name, record.tool_properties)
                if config.USE_PAILLIER:
                    private_key = paillier.PaillierPrivateKey(paillier.PaillierPublicKey(n), p, q)
                    if config.VALID:
                        comparisons = self._request_comparisons_provider(
                            map_id, record.map_name, n, record.points)
                        comparison_results_with_values = self._perform_comparisons_provider(
                            comparisons, private_key, record.points)
                        self._provide_records(comparison_results_with_values)
                    else:
                        public_key = private_key.public_key
                        points = [(ap, ae,
                                   public_key.encrypt(fz).ciphertext(),
                                   public_key.encrypt(usage).ciphertext())
                                   for ap, ae, fz, usage in record.points]
                        self.eval['encryption_time'] = time.monotonic()
                        self._provide_records_plaintext(map_id, record.map_name, points, n)
                else:
                    self._provide_records_plaintext(map_id, record.map_name, record.points)
            log.info(f"Provided {len(records)} records.")
        except Exception as e:
            log.exception(str(e))
            raise e

    def provide_from_file(self, file: str) -> None:
        """
        Return all records from file and store at map server.

        :param file: Path to the file containing the records
        """
        self.eval['start_time_file'] = time.monotonic()
        records = []
        with open(file, "r", encoding='utf-8') as fd:
            for line in fd:
                records.append(parse_record(line))
        self.eval['parsed_record_time'] = time.monotonic()
        log.info(f"Parsed {len(records)} records from {file}.")
        self.full_provide(records)

    def full_provide_eval(self, map_name: tuple[str, str, str],
                          tool_properties: tuple[str, int], p: int, s: int) -> None:
        """Provide records for evaluation purposes."""
        map_id, n, _, _ = self._retrieve_key_provider(map_name, tool_properties)
        j = {'map_id': map_id,
             'map_name': map_name,
             'n': n,
             'p': p,
             's': s}
        r = self.post(f"{self.mapserver}/provide_records_eval", json=j)
        suc = r.json()['success']
        if suc:
            log.debug("Successfully provided eval records.")
        else:
            msg = r.json()['msg']
            raise RuntimeError(f"Failed to provide eval records: {msg}")

    def _sql_eval(self, map_name: tuple[str, str, str],
                  tool_properties: tuple[str, int], p: int) -> tuple[float, float]:
        """Measure SQL query speed for evaluation."""
        map_id, n, _, _ = self._retrieve_key_provider(map_name, tool_properties)

        j = {'map_id': map_id,
             'map_name': map_name,
             'n': n,
             'p': p}
        start = time.monotonic()
        r = self.post(f"{self.mapserver}/provide_records_sql_eval", json=j)
        provision_time = time.monotonic() - start
        suc = r.json()['success']
        if suc:
            log.debug("Successfully provided eval records.")
        else:
            msg = r.json()['msg']
            raise RuntimeError(f"Failed to provide eval records: {msg}")

        j = {'map_id': map_id}
        start = time.monotonic()
        r = self.post(f"{self.mapserver}/retrieve_points_sql_eval", json=j)
        retrieval_time = time.monotonic() - start
        suc = r.json()['success']
        if suc:
            log.debug("Successfully retrieved eval points.")
        else:
            msg = r.json()['msg']
            raise RuntimeError(f"Failed to provide eval records: {msg}")

        return (provision_time, retrieval_time)


def get_producer_parser() -> argparse.ArgumentParser:
    """Return argparser for producer application."""
    parser = argparse.ArgumentParser(description="Producer App")
    action_group = parser.add_mutually_exclusive_group(required=False)
    parser.add_argument("username", help="Name of User", type=str,
                          action="store")
    parser.add_argument("password", help="Password of User", type=str,
                          action="store")
    parser.add_argument('-e', "--eval", help="Eval communication file",
                          type=str, action="store", required=config.EVAL)
    parser.add_argument('-v', '--verbose', action='count', default=0,
                          help="Increase verbosity. (-v INFO, -vv DEBUG)")
    parser.add_argument('-a', '--apae', type=lambda a: tuple(map(int, a.split(','))), nargs='+',
                        action='store', help="Combinations of ap,ae for regular query.")
    action_group.add_argument('-m', '--map', type=str, action='store',
                              help="Pose regular query.")
    action_group.add_argument('-t', '--tool', type=str, action='store',
                              help="Pose reverse query.")
    action_group.add_argument('-c', '--choice', type=int, action='store',
                              help="Choose tool after reverse query.")
    action_group.add_argument("-f", "--load_file", type=str, action='store',
                              help="Store points from file.", dest="file")
    return parser


if __name__ == '__main__':  # pragma no cover
    parser = get_producer_parser()
    args = parser.parse_args()
    if args.verbose == 1:
        log.setLevel(logging.INFO)
    elif args.verbose == 2:
        log.setLevel(logging.DEBUG)
    prod = Producer(args.username)
    prod.set_password(args.password)

    try:
        if config.EVAL:
            com_file = args.eval
            if args.map:
                ap_ae_full = [(i+1, j+1)
                              for i in range(config.AP_PRECISION)
                              for j in range(config.AE_PRECISION)]
                map_name = args.map.replace(
                    '(', '').replace(
                    ')', '').replace(
                    '\'', '').split(', ')
                def exec_regular():
                    """
                    Execute regular query and catch errors.

                    :return: result, error
                    """
                    try:
                        return prod.regular_query(map_name, ap_ae_full), None
                    except Exception as e:
                        error = str(e)
                        log.exception(error)
                        return None, error

                if config.MEASURE_RAM:
                    ram_usage, (result, error) = memory_usage(
                        (exec_regular,),
                        interval=config.RAM_INTERVAL,
                        timestamps=True,
                        include_children=True,
                        max_usage=True,
                        retval=True,
                    )
                    prod.eval['result'] = result
                    prod.eval['ram_usage'] = ram_usage
                    prod.eval['error'] = error
                else:
                    result, error = exec_regular()
                    prod.eval['result'] = result
                    prod.eval['ram_usage'] = 'N/A'
                    prod.eval['error'] = error
                with open(com_file, "wb") as fd:
                    pickle.dump(prod.eval, fd)

            if args.tool:
                t_list = args.tool.replace(
                    '(', '').replace(
                    ')', '').replace(
                    '\'', '').split(', ')
                def exec_reverse():
                    """
                    Execute reverse query and catch errors.

                    :return: result, error
                    """
                    try:
                        return prod.reverse_query(t_list[:2], t_list[2:], []), None
                    except Exception as e:
                        error = str(e)
                        log.exception(error)
                        return None, error

                if config.MEASURE_RAM:
                    ram_usage, (result, error) = memory_usage(
                        (exec_reverse,),
                        interval=config.RAM_INTERVAL,
                        timestamps=True,
                        include_children=True,
                        max_usage=True,
                        retval=True,
                    )
                    prod.eval['result'] = result
                    prod.eval['ram_usage'] = ram_usage
                    prod.eval['error'] = error
                else:
                    result, error = exec_reverse()
                    prod.eval['result'] = result
                    prod.eval['ram_usage'] = 'N/A'
                    prod.eval['error'] = error
                with open(com_file, "wb") as fd:
                    pickle.dump(prod.eval, fd)

            if args.file:
                def exec_provision():
                    """
                    Execute provision and catch errors.

                    :return: result, error
                    """
                    try:
                        return prod.provide_from_file(args.file), None
                    except Exception as e:
                        error = str(e)
                        log.exception(error)
                        return None, error

                if config.MEASURE_RAM:
                    ram_usage, (result, error) = memory_usage(
                        (exec_provision,),
                        interval=config.RAM_INTERVAL,
                        timestamps=True,
                        include_children=True,
                        max_usage=True,
                        retval=True,
                    )
                    prod.eval['result'] = result
                    prod.eval['ram_usage'] = ram_usage
                    prod.eval['error'] = error
                else:
                    result, error = exec_provision()
                    prod.eval['result'] = result
                    prod.eval['ram_usage'] = 'N/A'
                    prod.eval['error'] = error
                with open(com_file, "wb") as fd:
                    pickle.dump(prod.eval, fd)
        else:
            if args.map:
                if not args.apae:
                    print("No (ap, ae) combinations requested.")
                    quit()
                ap_ae = args.apae
                map_name = args.map.replace(
                    '(', '').replace(
                    ')', '').replace(
                    '\'', '').split(', ')
                result = prod.regular_query(map_name, ap_ae)
                if result:
                    print(result)
                    ap = [ap for ap, ae, fz, usage in result]
                    ae = [ae for ap, ae, fz, usage in result]
                    fz = [fz for ap, ae, fz, usage in result]
                    plot_ap_ae_fz(ap, ae, fz)

            if args.tool:
                t_list = args.tool.replace(
                    '(', '').replace(
                    ')', '').replace(
                    '\'', '').split(', ')
                result = prod.reverse_query(t_list[:2], t_list[2:], [])
                if result:
                    for r in result:
                        print(r)
                    map_ids = [map_id for map_id, points in result]
                    for map_id in map_ids:
                        offset, tool = prod.reverse_query_choice(map_id)
                        print(offset)
                        print(tool)

            if args.choice:
                map_id = args.choice
                result = prod.reverse_query_choice(map_id)

            if args.file:
                prod.provide_from_file(args.file)
    except Exception as e:
        log.error(str(e), exc_info=True)
        sys.exit()
