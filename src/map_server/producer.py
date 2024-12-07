"""
Producer pages of map server

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import logging

from flask import Blueprint, jsonify, request
from flask_httpauth import HTTPBasicAuth

from src.lib.user import UserType
from src.lib.server import gen_token, verify_token, producer_pw
from src.lib.map_server_backend import MapServer


log: logging.Logger = logging.getLogger(__name__)

bp = Blueprint('/producer', __name__, url_prefix='/producer')
producer_auth = HTTPBasicAuth()


@bp.route('/gen_token')
@producer_pw.login_required
def producer_gen_token() -> str:
    """
    Generate new token for logged-in producer.

    :return: JSON containing error message on failure or token on success
    """
    return gen_token(UserType.Producer, producer_pw.username())


@producer_auth.verify_password
def producer_verify_token(producer: str, token: str) -> bool:
    """
    Verify whether given token is valid for this producer.

    :param producer: Username of producer
    :param token: Token to verify
    :return: True if token is valid for producer, False otherwise
    """
    return verify_token(UserType.Producer, producer, token)


@bp.route('/request_comparisons_client', methods=['POST'])
@producer_auth.login_required
def request_comparisons_client() -> str:
    """
    Prepare and return comparisons for authenticated client.
    Requires JSON as POST data:
    {
        'map_id': map_id,
        'ap_ae': ap_ae
    }

    :return: Dict containing list of comparisons or error msg
    """
    log.debug("Producer request_comparisons_client accessed.")
    try:
        content = request.json
        map_id = content['map_id']
        ap_ae = content['ap_ae']
        comparisons = MapServer.get_comparisons_client(
            map_id, ap_ae, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'comparisons': comparisons})


@bp.route('/request_comparisons_provider', methods=['POST'])
@producer_auth.login_required
def request_comparisons_provider() -> str:
    """
    Prepare and return comparisons for authenticated provider.
    Requires JSON as POST data:
    {
        'map_id': map_id,
        'map_name': map_name,
        'n': n,
        'ap_ae': ap_ae
    }

    :return: Dict containing list of comparisons or error msg
    """
    log.debug("Producer request_comparisons_provider accessed.")
    try:
        content = request.json
        map_id = content['map_id']
        map_name = content['map_name']
        n = content['n']
        ap_ae = content['ap_ae']
        comparisons = MapServer.get_comparisons_provider(
            map_id, map_name, n, ap_ae, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'comparisons': comparisons})


@bp.route('/retrieve_points', methods=['POST'])
@producer_auth.login_required
def retrieve_points() -> str:
    """
    Retrieve points for authenticated producer.
    Requires JSON as POST data:
    {'comparison_results': comparison_results}

    :return: Dict containing list of points or error msg
    """
    log.debug("Producer retrieve_points accessed.")
    try:
        comparison_results = request.json['comparison_results']
        points = MapServer.get_points(comparison_results, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'points': points})


@bp.route('/retrieve_points_plaintext', methods=['POST'])
@producer_auth.login_required
def retrieve_points_plaintext() -> str:
    """
    Retrieve plaintext points for authenticated producer.
    Requires JSON as POST data:
    {
        'map_id': map_id,
        'ap_ae': ap_ae
    }

    :return: Dict containing list of points or error msg
    """
    log.debug("Producer retrieve_points_plaintext accessed.")
    try:
        content = request.json
        map_id = content['map_id']
        ap_ae = content['ap_ae']
        points = MapServer.get_points_plaintext(map_id, ap_ae, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'points': points})


@bp.route('/retrieve_previews', methods=['POST'])
@producer_auth.login_required
def retrieve_previews() -> str:
    """
    Retrieve previews for authenticated producer.
    Requires JSON as POST data:
    {'map_ids': Map IDs [int]}

    :return: Dict containing list of previews of error msg
    """
    log.debug("Producer retrieve_previews accessed.")
    try:
        map_ids = request.json['map_ids']
        previews = MapServer.get_previews(map_ids, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'previews': previews})

@bp.route('/retrieve_previews_plaintext', methods=['POST'])
@producer_auth.login_required
def retrieve_previews_plaintext() -> str:
    """
    Retrieve plaintext previews for authenticated producer.
    Requires JSON as POST data:
    {'map_ids': Map IDs [int]}

    :return: Dict containing list of previews or error msg
    """
    log.debug("Producer retrieve_previews_plaintext accessed.")
    try:
        map_ids = request.json['map_ids']
        previews = MapServer.get_previews_plaintext(map_ids, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'previews': previews})


@bp.route('/retrieve_preview_info', methods=['POST'])
@producer_auth.login_required
def retrieve_preview_info() -> str:
    """
    Retrieve previews for authenticated producer.
    Requires JSON as POST data:
    {'map_id': Map ID [int]}

    :return: Dict containing preview info or error msg
    """
    log.debug("Producer retrieve_preview_info accessed.")
    try:
        map_id = request.json['map_id']
        info = MapServer.get_preview_info(map_id, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'info': info})


@bp.route('/provide_records', methods=['POST'])
@producer_auth.login_required
def provide_records() -> str:
    """
    Store records provided by authenticated producer.
    Requires JSON as POST data:
    {'comparison_results_with_values': comparison_results_with_values}
    """
    log.debug("Producer provide_records accessed.")
    try:
        comparison_results_with_values = request.json['comparison_results_with_values']
        MapServer.store_records(comparison_results_with_values, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'msg': None})


@bp.route('/provide_records_plaintext', methods=['POST'])
@producer_auth.login_required
def provide_records_plaintext() -> str:
    """
    Store plaintext records provided by authenticated producer.
    Requires JSON as POST data:
    {
        'map_id': map_id,
        'map_name': map_name,
        'points': points,
        'n': n
    }
    """
    log.debug("Producer provide_records_plaintext accessed.")
    try:
        content = request.json
        map_id = content['map_id']
        map_name = content['map_name']
        points = content['points']
        n = content['n']
        MapServer.store_records_plaintext(map_id, map_name, n, points, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'msg': None})


@bp.route('/provide_records_eval', methods=['POST'])
@producer_auth.login_required
def provide_records_eval() -> str:
    """
    Store eval records provided by authenticated producer.
    Requires JSON as POST data:
    {
        'map_id': map_id,
        'map_name': map_name,
        'n': n,
        'p': p,
        's': s
    }
    """
    log.debug("Producer provide_records_eval accessed.")
    try:
        content = request.json
        map_id = content['map_id']
        map_name = content['map_name']
        n = content['n']
        p = content['p']
        s = content['s']
        MapServer._store_records_eval(map_id, map_name, n, p, s, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'msg': None})


@bp.route('/provide_records_sql_eval', methods=['POST'])
@producer_auth.login_required
def provide_records_sql_eval() -> str:
    """
    Store eval records provided by authenticated producer.
    Requires JSON as POST data:
    {
        'map_id': map_id,
        'map_name': map_name,
        'n': n,
        'p': p
    }
    """
    log.debug("Producer provide_records_eval accessed.")
    try:
        content = request.json
        map_id = content['map_id']
        map_name = content['map_name']
        n = content['n']
        p = content['p']
        MapServer._store_records_sql_eval(map_id, map_name, n, p, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'msg': None})


@bp.route('/retrieve_points_sql_eval', methods=['POST'])
@producer_auth.login_required
def retrieve_points_sql_eval() -> str:
    """
    Get points for SQL eval.
    Requires JSON as POST data:
    {
        'map_id': map_id,
        'p': p
    }
    """
    log.debug("Producer retrieve_points_eval accessed.")
    try:
        content = request.json
        map_id = content['map_id']
        MapServer._get_points_sql_eval(map_id, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'msg': None})
