"""
Map server backend

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import logging
import os
import random
import time

from sqlalchemy import tuple_
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from phe import paillier

from src.lib import config
from src.lib.helpers import print_time
from src.lib.user import UserType
from src.lib.user_database import Producer, db, get_user
from src.map_server.map_database import (ReverseQuerist, MapKey, StoredPoint, MapUsage,
                                         RetrievalProducer, BillingProducer,
                                         PreviewBilling, OffsetBilling)


log: logging.Logger = logging.getLogger(__name__)


class MapServer:
    """Map server of the platform"""

    def __init__(self, data_dir=config.DATA_DIR) -> None:
        """Set data directory and create it, if it does not exist."""
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(data_dir + '/logs/', exist_ok=True)

    @staticmethod
    def _prepare_comparisons(points: list[StoredPoint],
                             producer: Producer
                             ) -> list[tuple[int, int | None, int | None, int | None]]:
        """
        Prepare comparisons for producer.

        :param points: List of StoredPoints to prepare comparisons for
        :param producer: Producer involved in comparisons
        :return: List of tuples containing shifted fz values for each relevant
            StoredPoint [(point_id, fz_optimal, fz_pending, fz_unknown)]
        """

        comparisons = []
        for point in points:
            if point.last_comparator != producer or config.EVAL:
                comparisons.append(
                    (point.id, point.fz_optimal, point.fz_pending, point.fz_unknown))
            else: # needed for provider > provider, speeds up client > provider / provider > client
                comparisons.append((point.id, None, None, None))
            if producer not in point.open_requests:
                point.open_requests.append(producer)
            if producer not in point.current_comparators:
                point.current_comparators.append(producer)
        db.session.commit()
        return comparisons

    @staticmethod
    def _store_comparison(comparison_result: tuple[int, int, int],
                          producer: Producer) -> StoredPoint:
        """
        Store one comparison performed by producer and return point.
        
        :param comparison_result: Comparison results for one point
            (point_id, result_optimal_pending, result_optimal_unknown)
        :param producer: Producer involved in comparison
        :return: Retrieved point (ap, ae, fz, usage)
        """
        point_id, result_optimal_pending, result_optimal_unknown = comparison_result

        try:
            point = StoredPoint.query.filter(StoredPoint.id == point_id).one()
            public_key = paillier.PaillierPublicKey(point.map.public_key_n)
        except NoResultFound as e:
            log.exception(str(e))
            raise ValueError from e
        if producer not in point.open_requests:
            raise ValueError("Producer did not properly request comparison.")
        if producer in point.current_comparators:
            try:
                if point.last_comparator != producer or config.EVAL:
                    if result_optimal_pending:
                        if not point.fz_pending:
                            raise ValueError("Comparison was unasked for.")
                        if result_optimal_pending != point.fz_optimal:
                            raise ValueError("Latest comparison could not be verified, "
                                             "please contact platform operators.")
                        point.fz_pending = None
                        point.provider_pending = None
                    elif point.fz_pending:
                        raise ValueError("Comparison was not verified.")

                    if result_optimal_unknown:
                        if not point.fz_unknown:
                            raise ValueError("Comparison was unasked for.")
                        if result_optimal_unknown == point.fz_unknown:
                            point.fz_pending = point.fz_optimal
                            point.provider_pending = point.provider_optimal
                            point.fz_optimal = result_optimal_unknown
                            point.provider_optimal = point.provider_unknown
                            point.point_vendees.clear()
                        else:
                            if result_optimal_unknown != point.fz_optimal:
                                raise ValueError("Comparison result is not valid.")
                            if point.provider_optimal == point.provider_unknown:
                                raise ValueError("Last provider provided sub-optimal value, "
                                                 "please contact platform operators.")
                            point.fz_pending = point.fz_unknown
                            point.provider_pending = point.provider_unknown
                        if not config.EVAL:
                            point.fz_unknown = None
                            point.provider_unknown = None
                    elif point.fz_unknown:
                        raise ValueError("Comparison was not performed.")

                    point.last_comparator = producer
                    point.current_comparators.clear()
                    old_offset = point.current_offset
                    new_offset = random.randint(-config.FZ_PRECISION, config.FZ_PRECISION)
                    point.current_offset = new_offset
                    if point.fz_optimal:
                        fz_optimal_ct = (paillier.EncryptedNumber(public_key, point.fz_optimal)
                                         - old_offset + new_offset).ciphertext()
                        if config.EVAL:
                            fz_optimal_ct = point.fz_optimal
                        point.fz_optimal = fz_optimal_ct
                    if point.fz_pending:
                        fz_pending_ct = (paillier.EncryptedNumber(public_key, point.fz_pending)
                                         - old_offset + new_offset).ciphertext()
                        if config.EVAL:
                            fz_pending_ct = point.fz_pending
                        point.fz_pending = fz_pending_ct
                else:
                    if result_optimal_pending or result_optimal_unknown:
                        raise ValueError("Comparison was unasked for.")
                    point.current_comparators.remove(producer)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise ValueError from e

        return point

    @staticmethod
    def _add_to_retrieval_db_producer(points: list[StoredPoint],
                                      client: Producer) -> RetrievalProducer:
        """
        Create a retrieval transaction and store number of retrieved points
        for producer.

        :param points: Points retrieved from the database
        :param client: Client performing the query
        :return: Newly created RetrievalProducer
        """
        try:
            t = RetrievalProducer(client=client,
                                  point_count=len(points))
            db.session.add(t)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError from e
        return t

    @staticmethod
    def _add_to_billing_db_producer(points: list[StoredPoint],
                                    client: Producer,
                                    retrieval: RetrievalProducer) -> None:
        """
        Compute and store billing information for producer.

        :param retrieval: Corresponding RetrievalProducer
        :param points: Points retrieved from the database
        :param client: Client performing the query
        """
        # Count per provider
        providers = {}
        for point in points:
            if point.provider_optimal in providers:
                providers[point.provider_optimal] += 1
            else:
                providers[point.provider_optimal] = 1
        # Add to billing db
        billing = []
        for provider, count in providers.items():
            t = BillingProducer(provider=provider,
                                count_provider=count,
                                client=client,
                                retrieval=retrieval)
            billing.append(t)
        try:
            db.session.add_all(billing)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError from e

    @staticmethod
    def get_comparisons_client(map_id: int, ap_ae: list[tuple[int, int]],
                               producer: str) -> list[tuple[int, int, int, int]]:
        """
        Get comparisons for client.

        :param map_id: Map ID
        :param ap_ae: List of tuples of cutting depth/width values [(ap, ae)]
        :param producer: Username of client
        :return: List of tuples containing fz values for each relevant
            StoredPoint (point_id, fz_optimal, fz_pending, fz_unknown)
        """
        start = time.monotonic()
        log.debug("Get comparisons client called.")
        log.info("Getting comparisons...")
        client= get_user(UserType.Producer, producer)

        try:
            map_key = MapKey.query.filter(
                MapKey.map_id == map_id).one()
        except NoResultFound as e:
            log.exception(str(e))
            raise ValueError from e
        if any(querist.producer == client for querist in map_key.reverse_querists):
            raise ValueError("Producer already reverse-queried given map.")

        points: list[StoredPoint] = StoredPoint.query.filter(
            StoredPoint.map_id == map_id,
            tuple_(StoredPoint.ap, StoredPoint.ae).in_(ap_ae),
            StoredPoint.fz_optimal.is_not(None),
            StoredPoint.provider_optimal != client,
            StoredPoint.provider_unknown != client,
            ~StoredPoint.point_vendees.any(
                Producer.username == producer)).all()
        if not points:
            raise ValueError("No relevant points stored.")
        if client not in map_key.past_requests:
            map_key.past_requests.append(client)
        comparisons = MapServer._prepare_comparisons(points, client)

        log.info( f"Getting comparisons took: {print_time(time.monotonic()-start)}")
        return comparisons

    @staticmethod
    def get_points(comparison_results: list[tuple[int, int, int]],
                   producer: str) -> list[tuple[int, int, int, int]]:
        """
        Store comparisons performed by client and retrieve points.
        
        :param comparison_results: List of comparison results by point
            [(point_id, result_optimal_pending, result_optimal_unknown)]
        :param producer: Username of client
        :return: List of retrieved points [(ap, ae, fz, usage)]
        """
        start = time.monotonic()
        log.debug("Get points called.")
        log.info("Querying for points...")
        client = get_user(UserType.Producer, producer)

        points = []
        try:
            for result in comparison_results:
                point = MapServer._store_comparison(result, client)
                point.open_requests.remove(client)
                if not config.EVAL:
                    point.point_vendees.append(client)
                points.append(point)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError from e

        t = MapServer._add_to_retrieval_db_producer(points, client)
        MapServer._add_to_billing_db_producer(points, client, t)

        public_key = paillier.PaillierPublicKey(points[0].map.public_key_n)
        points = [
            (point.ap, point.ae,
             (paillier.EncryptedNumber(
                public_key, point.fz_optimal) - point.current_offset).ciphertext(),
             point.usage_total)
            for point in points
        ]

        log.info( f"Point query took: {print_time(time.monotonic()-start)}")
        return points

    @staticmethod
    def get_points_plaintext(map_id: int, ap_ae: list[tuple[int, int]],
                             producer: str) -> list[tuple[int, int, int, int]]:
        """
        Retrieve plaintext points.
        
        :param map_id: Map ID
        :param ap_ae: List of tuples of cutting depth/width values [(ap, ae)]
        :return: List of retrieved points [(ap, ae, fz, usage)]
        """
        if config.USE_PAILLIER and config.VALID:
            raise RuntimeError("Plaintext retrieval not allowed for secure scheme!")
        start = time.monotonic()
        log.debug("Get points plaintext called.")
        log.info("Querying for plaintext points...")
        client = get_user(UserType.Producer, producer)

        points: list[StoredPoint] = StoredPoint.query.filter(
            StoredPoint.map_id == map_id,
            tuple_(StoredPoint.ap, StoredPoint.ae).in_(ap_ae),
            StoredPoint.fz_optimal > 0,
            StoredPoint.provider_optimal != client,
            StoredPoint.provider_unknown != client,
            ~StoredPoint.point_vendees.any(
                Producer.username == producer)).all()
        if not points:
            raise ValueError("No relevant points stored.")
        for point in points:
            if not config.EVAL:
                point.point_vendees.append(client)

        t = MapServer._add_to_retrieval_db_producer(points, client)
        MapServer._add_to_billing_db_producer(points, client, t)

        log.info( f"Plaintext point query took: {print_time(time.monotonic()-start)}")
        return [
            (point.ap, point.ae, point.fz_optimal, point.usage_total)
            for point in points
        ]

    @staticmethod
    def get_previews(map_ids: list[int], producer: Producer
                     ) -> list[tuple[int, list[tuple[int, int, int, int]]]]:
        """
        Get map previews for given map IDS.
        Store access into billing database.

        :param map_ids: Map IDs
        :param producer: Username of producer requesting the preview
        :return: List of previews, each of which is a tuple of map_id,
            and list of points with shifted fz values
            [(ap, ae, shifted_fz_ct, usage_ct)]
        """
        start = time.monotonic()
        log.debug("Get previews called.")
        log.info("Querying for previews...")
        client = get_user(UserType.Producer, producer)

        previews = []
        querists = []
        billing = []
        for map_id in map_ids:
            map_key = MapKey.query.filter(
                MapKey.map_id == map_id).one_or_none()
            if not map_key:
                raise ValueError("Requested map not stored.")
            if any(querist.producer == client for querist in map_key.reverse_querists):
                raise ValueError("Producer already reverse-queried given map.")
            if client in map_key.past_requests:
                raise ValueError("Producer already regular-queried given map.")
            points = StoredPoint.query.filter(
                StoredPoint.map_id == map_id,
                StoredPoint.fz_optimal.is_not(None)).all()
            point_count = len(points)
            if not point_count:
                continue

            preview_points = []
            preview_offset = random.randint(-config.FZ_PRECISION, config.FZ_PRECISION)
            public_key = paillier.PaillierPublicKey(map_key.public_key_n)
            for point in points:
                offset = preview_offset - point.current_offset
                shifted_fz = paillier.EncryptedNumber(
                    public_key, point.fz_optimal) + offset
                preview_points.append(
                    (point.ap, point.ae, shifted_fz.ciphertext(), point.usage_total))
            previews.append((map_key.map_id, preview_points))

            querist = ReverseQuerist(producer=client,
                                     point_count=point_count,
                                     offset=offset,
                                     tool=map_key.tool)
            if not config.EVAL:
                map_key.reverse_querists.append(querist)
            querists.append(querist)
            t = PreviewBilling(client=client,
                               map=map_key)
            billing.append(t)

        if not previews:
            raise ValueError("No relevant points stored.")

        try:
            db.session.add_all(querists)
            db.session.add_all(billing)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError from e

        log.info( f"Preview query took: {print_time(time.monotonic()-start)}")
        return previews

    @staticmethod
    def get_previews_plaintext(map_ids: list[int], producer: Producer
                               ) -> list[tuple[int, list[tuple[int, int, int, int]]]]:
        """
        Get plaintext map previews for given map IDs.
        Store access into billing database.

        :param map_ids: Map IDs
        :param producer: Username of producer requesting the preview
        :return: List of previews, each of which is a tuple of map_id
            and list of points with shifted fz values
            [(ap, ae, shifted_fz, usage)]
        """
        if config.USE_PAILLIER:
            raise RuntimeError("Plaintext retrieval not allowed for secure scheme!")
        start = time.monotonic()
        log.debug("Get previews plaintext called.")
        log.info("Querying for plaintext previews...")
        client = get_user(UserType.Producer, producer)

        previews = []
        querists = []
        billing = []
        for map_id in map_ids:
            map_key = MapKey.query.filter(
                MapKey.map_id == map_id).one_or_none()
            if not map_key:
                raise ValueError("Requested map not stored.")
            if any(querist.producer == client for querist in map_key.reverse_querists):
                raise ValueError("Producer already reverse-queried given map.")
            if client in map_key.past_requests:
                raise ValueError("Producer already regular-queried given map.")
            points = StoredPoint.query.filter(
                StoredPoint.map_id == map_id,
                StoredPoint.fz_optimal > 0).all()
            point_count = len(points)
            if not point_count:
                continue

            preview_points = []
            offset = random.randint(-config.FZ_PRECISION, config.FZ_PRECISION)
            for point in points:
                shifted_fz = point.fz_optimal + offset
                preview_points.append((point.ap, point.ae, shifted_fz, point.usage_total))
            previews.append((map_key.map_id, preview_points))

            querist = ReverseQuerist(producer=client,
                                     point_count=point_count,
                                     offset=offset,
                                     tool=map_key.tool)
            if not config.EVAL:
                map_key.reverse_querists.append(querist)
            querists.append(querist)
            t = PreviewBilling(client=client,
                               map=map_key)
            billing.append(t)

        if not previews:
            raise ValueError("No relevant points stored.")

        try:
            db.session.add_all(querists)
            db.session.add_all(billing)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError from e

        log.info( f"Plaintext preview query took: {print_time(time.monotonic()-start)}")
        return previews

    @staticmethod
    def get_preview_info(map_id: int, producer: Producer) -> tuple[int, str]:
        """
        Get offset used in map preview and tool name.
        Store access into billing database.

        :param map_id: Map key ID
        :param producer: Username of producer requesting the previews
        :return: Offset used in preview
        """
        client = get_user(UserType.Producer, producer)

        map_key = MapKey.query.filter(
            MapKey.map_id == map_id).one_or_none()
        if not map_key:
            raise ValueError("Requested map not stored.")
        reverse_querist = ReverseQuerist.query.filter(
            ReverseQuerist.map_id == map_key.map_id,
            ReverseQuerist.producer == client).one_or_none()
        if not reverse_querist:
            raise ValueError("Producer never reverse-queried given map.")
        point_count = reverse_querist.point_count
        offset = reverse_querist.offset
        tool = reverse_querist.tool
        map_key.reverse_querists.remove(reverse_querist)
        map_key.past_requests.append(client)
        db.session.delete(reverse_querist)
        db.session.commit()

        try:
            t = OffsetBilling(client=client,
                              point_count=point_count)
            db.session.add(t)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError from e

        return (offset, tool)

    @staticmethod
    def get_comparisons_provider(map_id: int, map_name: tuple[str, str, str], n: int,
                                 ap_ae: list[tuple[int, int]], producer: str
                                 ) -> list[tuple[int, int, int, int]]:
        """
        Get comparisons for provider.

        :param map_id: Map ID
        :param n: n value of public key
        :param map_name: Map name (machine, material, tool)
        :param ap_ae: List of tuples of cutting depth/width values (ap, ae)
        :param producer: Username of provider
        :return: List of tuples containing fz values for each relevant
            StoredPoint [(point_id, fz_optimal, fz_pending, fz_unknown)]
        """
        start = time.monotonic()
        log.debug("Get comparisons provider called.")
        log.info("Getting comparisons...")
        provider = get_user(UserType.Producer, producer)
        machine, material, tool = map_name

        try:
            map_key = MapKey.query.filter(
                MapKey.map_id == map_id,
                MapKey.machine == machine,
                MapKey.material == material,
                MapKey.tool == tool).one_or_none()
        except MultipleResultsFound as e:
            log.exception(str(e))
            raise ValueError from e
        if not map_key:
            log.debug("Requested map not stored, adding entry.")
            try:
                map_key = MapKey(map_id=map_id,
                                 machine=machine,
                                 material=material,
                                 tool=tool,
                                 public_key_n=n,
                                 first_provider=provider)
                db.session.add(map_key)
                db.session.commit() # necessary to set map_key.id
            except Exception as e:
                db.session.rollback()
                raise ValueError("Non-unique combination of map id and map name, "
                                 "please contact platform operators.") from e
        elif map_key.public_key_n != n:
            raise ValueError("Public key could not be confirmed, "
                             "please contact platform operators.")
        if any(querist.producer == provider for querist in map_key.reverse_querists):
            raise ValueError("Producer reverse-queried given map but never retrieved offset.")

        points = []
        try:
            map_usage: MapUsage = MapUsage.query.filter(
                MapUsage.map_id == map_id,
                MapUsage.provider == provider).one_or_none()
            if not map_usage:
                log.debug("No usage for map stored, adding entry.")
                map_usage = MapUsage(map=map_key,
                                     provider=provider)
                db.session.add(map_usage)

            for ap, ae in ap_ae:
                point: StoredPoint = StoredPoint.query.filter(
                    StoredPoint.map_id == map_id,
                    StoredPoint.ap == ap,
                    StoredPoint.ae == ae).one_or_none()
                if not point:
                    log.debug("Requested point not stored, adding entry.")
                    offset = random.randint(
                        -config.FZ_PRECISION, config.FZ_PRECISION)
                    point = StoredPoint(map=map_key,
                                        ap=ap,
                                        ae=ae,
                                        current_offset=offset)
                    db.session.add(point)
                points.append(point)
            db.session.commit()
        except MultipleResultsFound as e:
            db.session.rollback()
            log.exception(str(e))
            raise ValueError from e
        except Exception as e:
            db.session.rollback()
            raise ValueError from e
        if provider not in map_key.past_requests:
            map_key.past_requests.append(provider)
        comparisons = MapServer._prepare_comparisons(points, provider)

        log.info( f"Getting comparisons took: {print_time(time.monotonic()-start)}")
        return comparisons

    @staticmethod
    def store_records(comparison_results_with_values:
                      list[tuple[int, int, int, int, int]],
                      producer: str) -> None:
        """
        Store comparisons performed by provider and store provided records.

        :param comparison_result_with_values: List of comparison results,
            extended with values to be provided
            [(point_id, result_optimal_pending, result_optimal_unknown, fz, usage)]
        :param producer: Username of provider
        """
        start = time.monotonic()
        log.debug("Store records called.")
        log.info("Storing records...")
        provider = get_user(UserType.Producer, producer)

        try:
            for results_values in comparison_results_with_values:
                results = tuple(results_values[:3])
                values = tuple(results_values[3:])
                fz, usage = values
                point = MapServer._store_comparison(results, provider)
                point.open_requests.remove(provider)

                map_id = point.map_id
                map_key = MapKey.query.filter(MapKey.map_id == map_id).one()
                public_key = paillier.PaillierPublicKey(map_key.public_key_n)
                map_usage: MapUsage = MapUsage.query.filter(
                    MapUsage.map_id == map_id,
                    MapUsage.provider == provider).one()

                if fz:
                    fz = paillier.EncryptedNumber(public_key, fz)
                    fz += point.current_offset
                    fz = fz.ciphertext()
                    if point.fz_optimal:
                        point.fz_unknown = fz
                        point.provider_unknown = provider
                    else:
                        point.fz_optimal = fz
                        point.provider_optimal = provider
                if usage:
                    usage = paillier.EncryptedNumber(public_key, usage)
                    stored_usage_total = point.usage_total
                    stored_usage_provider = map_usage.usage_provider
                    if stored_usage_total:
                        stored_usage_total = paillier.EncryptedNumber(
                            public_key, stored_usage_total)
                        stored_usage_total += usage
                    else:
                        stored_usage_total = usage
                    point.usage_total = stored_usage_total.ciphertext()
                    if stored_usage_provider:
                        stored_usage_provider = paillier.EncryptedNumber(
                            public_key, stored_usage_provider)
                        stored_usage_provider += usage
                    else:
                        stored_usage_provider = usage
                    map_usage.usage_provider = stored_usage_provider.ciphertext()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError from e

        log.info( f"Storing records took: {print_time(time.monotonic()-start)}")

    @staticmethod
    def store_records_plaintext(map_id: int, map_name: tuple[str, str, str], n: int,
                                points: list[tuple[int, int, int, int]],
                                producer: str) -> None:
        """
        Store provided plaintext records.

        :param map_id: Map ID
        :param map_name: Map name
        :param n: n value of public key
        :param points: List of points to be provided
            (ap, ae, fz, usage)
        :param producer: Username of provider
        """
        if config.USE_PAILLIER and config.VALID:
            raise RuntimeError("Plaintext storing not allowed for secure scheme!")
        start = time.monotonic()
        log.debug("Store records plaintext called.")
        log.info("Storing plaintext records...")
        provider = get_user(UserType.Producer, producer)
        machine, material, tool = map_name

        try:
            map_key = MapKey.query.filter(
                MapKey.map_id == map_id,
                MapKey.machine == machine,
                MapKey.material == material,
                MapKey.tool == tool).one_or_none()
            map_usage: MapUsage = MapUsage.query.filter(
                MapUsage.map_id == map_id,
                MapUsage.provider == provider).one_or_none()
        except MultipleResultsFound as e:
            log.exception(str(e))
            raise ValueError from e
        if not map_key:
            log.debug("Requested map not stored, adding entry.")
            try:
                map_key = MapKey(map_id=map_id,
                                 machine=machine,
                                 material=material,
                                 tool=tool,
                                 public_key_n=n,
                                 first_provider=provider)
                db.session.add(map_key)
                db.session.commit() # necessary to set map_key.id
            except Exception as e:
                db.session.rollback()
                raise ValueError("Non-unique combination of map id and map name, "
                                 "please contact platform operators.") from e
        if not map_usage:
            map_usage = MapUsage(map=map_key,
                                 provider=provider,
                                 usage_provider=0)
            db.session.add(map_usage)
            db.session.commit()
        if config.USE_PAILLIER:
            public_key = paillier.PaillierPublicKey(map_key.public_key_n)

        try:
            for ap, ae, fz, usage in points:
                point = StoredPoint.query.filter(
                    StoredPoint.map_id == map_id,
                    StoredPoint.ap == ap,
                    StoredPoint.ae == ae).one_or_none()
                if not point:
                    log.debug("Requested point not stored, adding entry.")
                    point = StoredPoint(map=map_key,
                                        ap=ap,
                                        ae=ae,
                                        usage_total=usage,
                                        fz_optimal=fz,
                                        provider_optimal=provider,
                                        current_offset=0)
                    db.session.add(point)
                else:
                    if fz:
                        if config.USE_PAILLIER:
                            point.fz_unknown = fz
                            point.provider_unknown = provider
                        elif fz > point.fz_optimal:
                            point.fz_optimal = fz
                            point.provider_optimal = provider
                    if usage:
                        stored_usage_total = point.usage_total
                        stored_usage_provider = map_usage.usage_provider
                        if config.USE_PAILLIER:
                            usage = paillier.EncryptedNumber(public_key, usage)
                            stored_usage_total = paillier.EncryptedNumber(
                                public_key, stored_usage_total)
                            stored_usage_total += usage
                            point.usage_total = stored_usage_total.ciphertext()
                            stored_usage_provider = paillier.EncryptedNumber(
                                public_key, stored_usage_provider)
                            stored_usage_provider += usage
                            map_usage.usage_provider = stored_usage_provider.ciphertext()
                        else:
                            point.usage_total = stored_usage_total + usage
                            map_usage.usage_provider = stored_usage_provider + usage
            db.session.commit()
        except MultipleResultsFound as e:
            log.exception(str(e))
            raise ValueError from e
        except Exception as e:
            db.session.rollback()
            raise ValueError from e

        log.info( f"Storing plaintext records took: {print_time(time.monotonic()-start)}")

    @staticmethod
    def _store_records_eval(map_id: int, map_name: tuple[str, str, str],
                            n: int, p: int, s: int, producer: str) -> None:
        """
        Store records for eval preparation.

        :param map_id: Map ID
        :param map_name: Map name
        :param n: n value of public key
        :param p: Number of points to be provided
        :param s: Number of values to store per point (either 1, 2, or 3)
        :param producer: Username of provider
        """
        if not config.EVAL:
            raise RuntimeError("Storing eval records only allowed in eval mode!")
        if s not in [1, 2, 3]:
            raise RuntimeError("Value of s must be either 1, 2, or 3!")
        log.info("Storing eval records...")
        provider = get_user(UserType.Producer, producer)
        machine, material, tool = map_name
        public_key = paillier.PaillierPublicKey(n)
        fz = random.randint(1, config.FZ_PRECISION)
        usage = random.randint(1, config.USAGE_PRECISION) * s
        if config.USE_PAILLIER:
            offset = random.randint(
                -config.FZ_PRECISION, config.FZ_PRECISION)
            fz = public_key.encrypt(fz+offset).ciphertext()
            usage = public_key.encrypt(usage).ciphertext()
        ap_ae = [(ap+1, ae+1)
                 for ap in range(config.AP_PRECISION)
                 for ae in range(config.AE_PRECISION)]
        ap_ae = ap_ae[:p]

        map_key = MapKey.query.filter(
            MapKey.map_id == map_id,
            MapKey.machine == machine,
            MapKey.material == material,
            MapKey.tool == tool).one_or_none()
        map_usage: MapUsage = MapUsage.query.filter(
            MapUsage.map_id == map_id,
            MapUsage.provider == provider).one_or_none()
        if not map_key:
            log.debug("Requested map not stored, adding entry.")
            map_key = MapKey(map_id=map_id,
                                machine=machine,
                                material=material,
                                tool=tool,
                                public_key_n=n,
                                first_provider=provider)
            db.session.add(map_key)
            db.session.commit() # necessary to set map_key.id
        if provider not in map_key.past_requests:
            map_key.past_requests.append(provider)
        if not map_usage:
            if config.USE_PAILLIER:
                map_usage = MapUsage(map=map_key,
                                    provider=provider)
            else:
                map_usage = MapUsage(map=map_key,
                                    provider=provider,
                                    usage_provider=0)
            db.session.add(map_usage)
            db.session.commit()

        for ap, ae in ap_ae:
            point = StoredPoint.query.filter(
                StoredPoint.map_id == map_id,
                StoredPoint.ap == ap,
                StoredPoint.ae == ae).one_or_none()
            if not point:
                log.debug("Requested point not stored, adding entry.")
                if config.USE_PAILLIER:
                    point = StoredPoint(map=map_key,
                                        ap=ap,
                                        ae=ae,
                                        current_offset=offset)
                else:
                    point = StoredPoint(map=map_key,
                                        ap=ap,
                                        ae=ae,
                                        usage_total=0,
                                        fz_optimal=0)
                db.session.add(point)

            point.fz_optimal = fz
            point.provider_optimal = provider
            if s > 1:
                point.fz_unknown = fz
                point.provider_unknown = provider
            if s > 2:
                point.fz_pending = fz
                point.provider_pending = provider
            point.usage_total = usage
            map_usage.usage_provider = usage
        db.session.commit()

    @staticmethod
    def _store_records_sql_eval(map_id: int, map_name: tuple[str, str, str],
                                n: int, p: int, producer: str) -> None:
        """
        Store records for SQL eval.

        :param map_id: Map ID
        :param map_name: Map name
        :param n: n value of public key
        :param p: Number of points to be provided
        :param producer: Username of provider
        """
        if not config.EVAL:
            raise RuntimeError("Storing eval records only allowed in eval mode!")
        log.info("Storing eval records...")
        provider = get_user(UserType.Producer, producer)
        machine, material, tool = map_name
        public_key = paillier.PaillierPublicKey(n)
        fz_dummy = random.randint(1, config.FZ_PRECISION)
        usage_dummy = random.randint(1, config.USAGE_PRECISION)
        offset = random.randint(-config.FZ_PRECISION, config.FZ_PRECISION)
        ap_ae = [(ap+1, ae+1)
                 for ap in range(config.AP_PRECISION)
                 for ae in range(config.AE_PRECISION)]
        ap_ae = ap_ae[:p]

        map_key = MapKey.query.filter(
            MapKey.map_id == map_id,
            MapKey.machine == machine,
            MapKey.material == material,
            MapKey.tool == tool).one_or_none()
        map_usage: MapUsage = MapUsage.query.filter(
            MapUsage.map_id == map_id,
            MapUsage.provider == provider).one_or_none()
        if not map_key:
            log.debug("Requested map not stored, adding entry.")
            map_key = MapKey(map_id=map_id,
                                machine=machine,
                                material=material,
                                tool=tool,
                                public_key_n=n,
                                first_provider=provider)
            db.session.add(map_key)
            db.session.commit() # necessary to set map_key.id
        if provider not in map_key.past_requests:
            map_key.past_requests.append(provider)
        if not map_usage:
            map_usage = MapUsage(map=map_key,
                                 provider=provider)
            db.session.add(map_usage)
            db.session.commit()

        for ap, ae in ap_ae:
            point = StoredPoint.query.filter(
                StoredPoint.map_id == map_id,
                StoredPoint.ap == ap,
                StoredPoint.ae == ae).one_or_none()
            if not point:
                log.debug("Requested point not stored, adding entry.")
                point = StoredPoint(map=map_key,
                                    ap=ap,
                                    ae=ae,
                                    usage_total=usage_dummy,
                                    fz_optimal=fz_dummy,
                                    provider_optimal=provider,
                                    current_offset=offset)
                db.session.add(point)

            fz = paillier.EncryptedNumber(public_key, fz_dummy)
            fz += point.current_offset
            fz = fz.ciphertext()
            point.fz_unknown = fz
            point.provider_unknown = provider

            usage = paillier.EncryptedNumber(public_key, usage_dummy)
            stored_usage_total = point.usage_total
            stored_usage_provider = map_usage.usage_provider
            if stored_usage_total:
                stored_usage_total = paillier.EncryptedNumber(
                    public_key, stored_usage_total)
                stored_usage_total += usage
            else:
                stored_usage_total = usage
            point.usage_total = stored_usage_total.ciphertext()
            if stored_usage_provider:
                stored_usage_provider = paillier.EncryptedNumber(
                    public_key, stored_usage_provider)
                stored_usage_provider += usage
            else:
                stored_usage_provider = usage
            map_usage.usage_provider = stored_usage_provider.ciphertext()
        db.session.commit()

    @staticmethod
    def _get_points_sql_eval(map_id: int, producer: str) -> list[tuple[int, int, int, int]]:
        """
        Retrieve points for SQL eval.
        
        :param map_id: Map ID
        :param ap_ae: List of tuples of cutting depth/width values [(ap, ae)]
        :return: List of retrieved points [(ap, ae, fz, usage)]
        """
        client = get_user(UserType.Producer, producer)
        ap_ae = [(i+1, j+1)
                 for i in range(config.AP_PRECISION)
                 for j in range(config.AE_PRECISION)]

        points: list[StoredPoint] = StoredPoint.query.filter(
            StoredPoint.map_id == map_id,
            tuple_(StoredPoint.ap, StoredPoint.ae).in_(ap_ae),
            StoredPoint.fz_optimal > 0).all()
        if not points:
            raise ValueError("No relevant points stored.")

        t = MapServer._add_to_retrieval_db_producer(points, client)
        MapServer._add_to_billing_db_producer(points, client, t)

        public_key = paillier.PaillierPublicKey(points[0].map.public_key_n)
        points = [
            (point.ap, point.ae,
             (paillier.EncryptedNumber(
                public_key, point.fz_optimal) - point.current_offset).ciphertext(),
             point.usage_total)
            for point in points
        ]

        return points
