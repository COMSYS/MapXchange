"""
CLI for user database

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import argparse
import logging

from flask import Flask

from src.lib import config
from src.lib.user_database import db
import src.lib.user_database as user_db


NO_PRINT = False
log: logging.Logger = logging.getLogger(__name__)


def get_db_parser() -> argparse.ArgumentParser:
    """Return an argument parser for the DB CLIs."""
    db_parser = argparse.ArgumentParser(description="DB CLI")
    action_group = db_parser.add_mutually_exclusive_group(required=True)
    db_parser.add_argument("username", help="Name of User", type=str,
                           action="store", nargs='?')
    db_parser.add_argument("password", help="Password of User", type=str,
                           action="store", nargs='?')
    action_group.add_argument("-a", "--add", action='store_true',
                              help="Add User with given username and password to DB."
                              )
    action_group.add_argument("-t", "--get_token", action='store_true',
                              help="Retrieve get_token for user with given "
                                   "username.")
    action_group.add_argument("--verify", action='store_true',
                              help="Verfiy that password is correct.")
    action_group.add_argument("-n", "--new", action="store", type=str,
                              dest="new",
                              help="Replace password for user with given username.")
    action_group.add_argument("-l", "--list", action="store_true",
                              help="List all existing users.")
    action_group.add_argument("-s", "--verify-token", action='store',
                              dest='token_val',
                              help="Verfiy that get_token is correct. ("
                                   "Destroys token, for testing only.)",
                              type=str)
    return db_parser


def output(*args: str) -> None:
    """Print either via print or via logging."""
    if not NO_PRINT:
        print(*args)
    else:
        log.info(" ".join([str(i) for i in args]))


def main(user_type: str, args: list[str], data_dir: str = config.DATA_DIR,
         no_print: bool = False) -> \
        None:
    """
    Manage the database according to the given CL arguments.
    (Update both databases)

    :param user_type: Type of database that shall be managed
    :param args: Command line arguments (argv[1:])
    :param data_dir: [optional] Directory where SQLite files are located
    :param no_print: [optional] Use log instead of print
    """
    global NO_PRINT
    NO_PRINT = no_print
    if len(args) > 0 and (args[0] == "-l" or args[0] == "--list"):
        # We want to skip mandatory args.
        show_list = True
    else:
        show_list = False
        args = get_db_parser().parse_args(args)
    databases = {
        'map': config.MAP_DB,
        'key': config.KEY_DB
    }
    for server, db_file in databases.items():
        app = Flask(__name__)
        app.config.from_mapping(
            SQLALCHEMY_DATABASE_URI=f"sqlite:///{data_dir}/{db_file}",
            SQLALCHEMY_TRACK_MODIFICATIONS=False
        )
        db.init_app(app)
        with app.app_context():
            # Init DB
            db.create_all()
            if show_list:
                users = user_db.get_all_users(user_type)
                output(f"> Result for {server.capitalize()}-Database: "
                       f"({len(users)} Users found.)")
                for i, user in enumerate(users):
                    output(f"{i}: {user}")
            else:
                if args.add:
                    try:
                        if args.username is None or args.password is None:
                            raise ValueError(
                                "Username and Password have to defined.")
                        user_db.add_user(user_type, args.username, args.password)
                        output(f"> {server.capitalize()}: Successfully added user "
                               f"{args.username}.")
                    except ValueError as e:
                        output(f"> {server.capitalize()}: Add user failed: {e}")
                elif args.get_token:
                    try:
                        if args.username is None or args.password is None:
                            raise ValueError(
                                "Username and Password have to defined.")
                        if user_db.verify_password(user_type, args.username,
                                                   args.password):
                            output(f"> {server.capitalize()} database: ",
                                   user_db.generate_token(user_type, args.username))
                        else:
                            output(f"> {server.capitalize()}: Incorrect password!")
                    except ValueError as e:
                        log.error(f"{server.capitalize()}: Token generation"
                                  f" failed: {e}")
                elif args.new is not None:
                    try:
                        if args.username is None or args.password is None:
                            raise ValueError(
                                "Username and Password have to defined.")
                        user_db.update_password(user_type, args.username,
                                                args.password, args.new)
                        output(
                            f"> {server.capitalize()}: Successfully updated"
                            f"password for user {args.username}.")
                    except ValueError as e:
                        log.error(f"{server.capitalize()}: "
                                  f"Password update failed: {e}")
                elif args.verify:
                    try:
                        if args.username is None or args.password is None:
                            raise ValueError(
                                "Username and Password have to defined.")
                        if user_db.verify_password(user_type, args.username,
                                                   args.password):
                            output(f"> {server.capitalize()}: "
                                   f"Credentials are correct.")
                        else:
                            output(f"> {server.capitalize()}: "
                                   f"Password is not correct.")
                    except ValueError as e:
                        log.error(f"{server.capitalize()}: Password verfication"
                                  f"failed: {e}")
                elif args.token_val is not None:
                    try:
                        if args.username is None:
                            raise ValueError("Username has to be defined.")
                        if user_db.verify_token(user_type,
                                                args.username, args.token_val):
                            output(f"> {server.capitalize()}: Token correct. "
                                   f"Token destroyed.")
                        else:
                            output(f"> {server.capitalize()}: Bad Token.")
                    except ValueError as e:
                        log.error(f"{server.capitalize()}: "
                                  f"Token verfication failed: {e}")
