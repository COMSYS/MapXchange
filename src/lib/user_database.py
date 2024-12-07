"""
User database

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import logging
import secrets
import sqlite3
from abc import abstractmethod
from typing import Callable

import sqlalchemy
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from src.lib.helpers import to_base64, from_base64
from src.lib.user import UserType


db = SQLAlchemy()
log: logging.Logger = logging.getLogger(__name__)


class SecurityInteger(db.TypeDecorator):
    """SQLAlchemy type decorator for integers related to security"""

    impl = db.TEXT

    cache_okay = True

    def process_bind_param(self, value, dialect):
        """Exceute on insert."""
        if value is not None:
            value = to_base64(value)
        return value

    def process_result_value(self, value, dialect):
        """Execute on select."""
        if value is not None:
            value = from_base64(value)
        return value


class Token(db.Model):
    """SQLAlchemy class representing one token"""

    __tablename__ = "tokens"

    id = db.Column(db.Integer,
                   nullable=False,
                   primary_key=True)  # Auto
    value = db.Column(db.Text, nullable=False)
    producer_id = db.Column(db.Integer,
                          db.ForeignKey("producers.id"))
    producer = db.relationship("Producer",
                               uselist=False,
                               back_populates="tokens")


class User:
    """Abstract base class for users"""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, nullable=False, unique=True)
    password = db.Column(db.Text, nullable=False)

    @property
    @abstractmethod
    def tokens(self):  # pragma no cover
        """List of tokens of user"""


class Producer(User, db.Model):
    """SQLAlchemy class representing producers"""

    __tablename__ = "producers"

    tokens = db.relationship("Token",
                             uselist=True,
                             back_populates="producer")


def verify_password(user_type: str, username: str, pwd: str) -> bool:
    """
    Return whether the password is correct for the user with the
    given user_id. Raises Value error if user does not exist.
    """
    UserCls = get_user_type(user_type)
    u: User = UserCls.query.filter_by(username=username).first()
    if u is None:
        raise ValueError(f"No {user_type} with name '{username}' exists.")
    return check_password_hash(u.password, pwd)


def verify_token(user_type: str, username: str, token: str):
    """
    Return whether the token is correct for the user with the
    given username.
    Furthermore, remove token hash from DB because tokens can only be
    used once.
    """
    UserCls = get_user_type(user_type)
    u: User = UserCls.query.filter_by(username=username).first()
    if u is None:
        raise ValueError(f"No {user_type} with name '{username}' exists.")
    tokens = u.tokens
    if len(u.tokens) == 0:
        msg = f"No token for user '{username}' exists."
        raise ValueError(msg)
    for t in tokens:
        if check_password_hash(t.value, token):
            logging.debug("Token correct.")
            # Remove token from DB
            db.session.delete(t)
            db.session.commit()
            return True
    return False


def _generate_token() -> str:
    """
    Generate a random token and return it along the corresponding
    SHA3 Hash.
    """
    token = secrets.token_urlsafe(64)
    return token


def generate_token(user_type: str, user_id: str):
    """Generate and return a new token for the user with the given ID."""
    UserCls = get_user_type(user_type)
    token = _generate_token()
    u: User = UserCls.query.filter_by(username=user_id).first()
    if u is None:
        raise ValueError(f"Could not generate token: No user '{user_id}' "
                         f"exists.")
    token_val = generate_password_hash(token, salt_length=32)
    t = Token(value=token_val)
    db.session.add(t)
    u.tokens.append(t)
    db.session.commit()
    log.info(f"Generated new token for '{user_id}'.")
    return token


def update_password(user_type: str, user_id: str, old_pwd: str, new_pwd: str):
    """Update the password if the credentials are correct."""
    UserCls = get_user_type(user_type)
    if not verify_password(user_type, user_id, old_pwd):
        msg = f"Password change for user '{user_id}' failed because old " \
              f'password is wrong.'
        raise ValueError(msg)
    if len(new_pwd) < 8:
        msg = "Password needs to have at least 8 characters!"
        raise ValueError(msg)
    pwd_hash = generate_password_hash(new_pwd, salt_length=32)
    u: UserCls = UserCls.query.filter_by(username=user_id).first()
    u.password = pwd_hash
    db.session.commit()
    log.info(f"Successfully updated password for '{user_id}'.")


def get_all_users(user_type: str) -> list[str]:
    """Return a list containing all user IDs"""
    UserCls = get_user_type(user_type)
    users = UserCls.query.all()
    return [u.username for u in users]


def add_user(user_type: str, username: str, password: str):
    """Add a new client, generate a token for API access and return it."""
    UserCls: Callable = get_user_type(user_type)
    if len(password) < 8:
        msg = "Password needs to have at least 8 characters!"
        raise ValueError(msg)
    pwd_hash = generate_password_hash(password, salt_length=32)
    token = generate_password_hash(_generate_token(), salt_length=32)
    try:
        u = UserCls(username=username, password=pwd_hash)
        t = Token(value=token)
        u.tokens.append(t)
        db.session.add(t)
        db.session.add(u)
        db.session.commit()
    except (sqlalchemy.orm.exc.FlushError,
            sqlalchemy.exc.InvalidRequestError,
            sqlalchemy.exc.IntegrityError,
            sqlite3.IntegrityError):
        db.session.rollback()
        msg = f"{user_type.capitalize()} username '{username}' already in use!"
        raise ValueError(msg)
    log.info(f"Successfully stored {user_type.capitalize()} '{username}' in DB.")
    return token


def get_user_type(user_type: str) -> User:
    """
    Return the class corresponding to the given user_type.

    :param user_type: Type of user
    :return: Class representing that user user_type.
    """
    if user_type == UserType.Producer:
        return Producer
    else:
        raise TypeError(f"No such User Type exists: {user_type}")


def get_user(user_type: str, username: str) -> Producer:
    """
    Return the user with the given username.
    
    :param user_type: Producer
    :param username: username to check
    :return: The user object
    """
    UserCls = get_user_type(user_type)
    c = UserCls.query.filter_by(username=username).first()
    if c is None:
        raise ValueError(
            f"{user_type.capitalize()} '{username}' does not exist!")
    return c
