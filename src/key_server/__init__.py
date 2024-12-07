"""
Application factory for key server app

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import os

from flask import Flask

from src.lib import config
import src.lib.user_database
from src.lib.user_database import db
from src.lib.logging import configure_root_logger


def create_app(test_config=None, logging_level=config.LOGLEVEL,
               data_dir=config.DATA_DIR) -> Flask:
    """Factory function for flask app. Return a configured flask app object."""

    app = Flask(__name__, instance_relative_config=True)
    if test_config is not None and 'DATA_DIR' in test_config:
        data_dir = test_config['DATA_DIR']
    log_dir = data_dir + 'logs/'
    app.config.from_mapping(
        DATA_DIR=data_dir,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{data_dir}/{config.KEY_DB}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is not None:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    # Update Logging with new values
    configure_root_logger(logging_level, log_dir + config.KEY_LOGFILE)

    from src.lib.key_server_backend import KeyServer
    from src.key_server import main, producer

    db.init_app(app)
    with app.app_context():
        db.create_all()

    # Include pages
    app.register_blueprint(main.bp)
    app.register_blueprint(producer.bp)

    KeyServer(app.config['DATA_DIR'])

    if config.EVAL:
        print("************************************************************")
        print("Starting in Eval Mode!")
        print("************************************************************")

    return app
