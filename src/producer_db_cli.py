#!/usr/bin/env python3
"""
CLI to interact with producer database

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import logging
import sys

from src.lib import db_cli, config
from src.lib.user import UserType
from src.lib.logging import configure_root_logger

if __name__ == '__main__':  # pragma no cover
    configure_root_logger(logging.INFO, config.LOG_DIR + "producer_db.log")
    log = logging.getLogger()
    db_cli.main(UserType.Producer, sys.argv[1:])
