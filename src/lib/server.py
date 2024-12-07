"""
Base server for map and key servers

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import logging

import flask.wrappers
from flask import jsonify, current_app as app
from flask_httpauth import HTTPBasicAuth

from src.lib.user import UserType
import src.lib.user_database as user_db


log: logging.Logger = logging.getLogger(__name__)


def gen_token(user_type: str, user: str) -> flask.wrappers.Response:
    """
    Generate and return a token for the given User.

    :param user_type: UserType.Producer
    :param user: Username
    :return: A Jsonify response that can directly be returned
    """
    log.debug('Token requested.')
    try:
        resp = jsonify(
            {'success': True,
             'token': user_db.generate_token(user_type, user)
             })
    except ValueError as e:
        log.warning("gen_token: " + str(e))
        resp = jsonify(
            {
                'success': False,
                'msg': str(e)
            }
        )
    return resp


def verify_token(user_type: str, user: str, token: str) -> bool:
    """Verify if the get_token is correct for the given user and return the
    username if so or raise an error otherwise."""
    if 'LOGIN_DISABLED' in app.config and app.config['LOGIN_DISABLED']:
        return True
    try:
        if not user_db.verify_token(user_type, user, token):
            return False
    except ValueError as e:
        log.warning(str(e))
        return False
    return True


producer_pw = HTTPBasicAuth()

@producer_pw.verify_password
def verify_producer_pw(user: str, pw: str) -> bool:
    """
    Verify that the credentials match those in the database.
    :param user: Username
    :param pw: Password
    :return: Authentication result.
    """
    if 'LOGIN_DISABLED' in app.config and app.config['LOGIN_DISABLED']:
        return True
    try:
        return user_db.verify_password(UserType.Producer, user, pw)
    except ValueError:
        return False
