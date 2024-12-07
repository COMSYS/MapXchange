"""
Producer pages of key server

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import logging

from flask import Blueprint, jsonify, request
from flask_httpauth import HTTPBasicAuth

from src.lib.user import UserType
from src.lib.server import gen_token, verify_token, producer_pw
from src.lib.key_server_backend import KeyServer


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


@bp.route('/retrieve_key_client', methods=['POST'])
@producer_auth.login_required
def retrieve_key_client() -> str:
    """
    Retrieve private key for authenticated producer.
    Requires JSON as POST data:
    {'map_name': map_name}

    :return: Dict containing map id and keys or error msg
    """
    log.debug("Producer retrieve_key_client accessed.")
    try:
        map_name = request.json['map_name']
        id_key = KeyServer.get_key_client_producer(map_name, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'id_key': id_key})


@bp.route('/retrieve_key_provider', methods=['POST'])
@producer_auth.login_required
def retrieve_key_provider() -> str:
    """
    Retrieve public map key for authenticated producer.
    Requires JSON as POST data:
    {
        'map_name': map_name,
        'tool_properties': tool_properties
    }

    :return: Dict containing map id and keys or error msg
    """
    log.debug("Producer retrieve_key_provider accessed.")
    try:
        content = request.json
        map_name = content['map_name']
        tool_properties = content['tool_properties']
        id_key = KeyServer.get_key_provider(map_name, tool_properties,
                                            producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'id_key': id_key})


@bp.route('/retrieve_map_ids', methods=['POST'])
@producer_auth.login_required
def retrieve_map_ids() -> str:
    """
    Retrieve map ids for authenticated producer.
    Requires JSON as POST data:
    {
        'map_name_prefix': map_name_prefix,
        'tool_properties': tool_properties,
        'excluded_tools': excluded_tools
    }

    :return: Dict containing list of map ids and keys or error msg
    """
    log.debug("Producer retrieve_map_ids accessed.")
    try:
        content = request.json
        map_name_prefix = content['map_name_prefix']
        tool_properties = content['tool_properties']
        excluded_tools = content['excluded_tools']
        ids_keys = KeyServer.get_map_ids(map_name_prefix, tool_properties,
                                         excluded_tools, producer_auth.username())
    except ValueError as e:
        return jsonify({'success': False,
                        'msg': str(e)})
    return jsonify({'success': True,
                    'ids_keys': ids_keys})
