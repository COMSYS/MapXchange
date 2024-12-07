"""
General configurations

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import logging
import os


# GENERAL----------------------------------------------------------------------
USE_PAILLIER = False
USE_TLS = False
DEBUG = False
EVAL = False
VALID = True
# -----------------------------------------------------------------------------
# PARAMETER MAP SETTINGS-------------------------------------------------------
AP_PRECISION = 250
AE_PRECISION = 250
FZ_PRECISION = 3000
USAGE_PRECISION = 100
MAP_SIZE = AP_PRECISION * AE_PRECISION
# -----------------------------------------------------------------------------
# DIRECTORY STRUCTURE----------------------------------------------------------
_cur_dir = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
WORKING_DIR = os.path.abspath(_cur_dir) + '/'
DATA_DIR = WORKING_DIR + 'data/'
EVAL_DIR = WORKING_DIR + 'eval_results/'
LOG_DIR = DATA_DIR + 'logs/'
# -----------------------------------------------------------------------------
# TLS--------------------------------------------------------------------------
TLS_CERT_DIR = DATA_DIR + "certs/"
TLS_ROOT_CA = TLS_CERT_DIR + "rootCA.crt"
# -----------------------------------------------------------------------------
# EVAL SETTINGS---------------------------------------------------------------
SETS = 30
RAM_INTERVAL = 0.5
MEASURE_RAM = False
if EVAL:
    DATA_DIR += 'eval/'
    os.makedirs(DATA_DIR, exist_ok=True)
TEMP_DIR = DATA_DIR + 'tmp/'
os.makedirs(TEMP_DIR, exist_ok=True)
# -----------------------------------------------------------------------------
# LOGGING----------------------------------------------------------------------
LOGLEVEL = logging.DEBUG
# -----------------------------------------------------------------------------
# KEY SERVER SETTINGS----------------------------------------------------------
KEY_HOSTNAME = "localhost"
KEY_API_PORT = 5000
KEY_TLS_CERT = TLS_CERT_DIR + "keyserver.crt"
KEY_TLS_KEY = TLS_CERT_DIR + "keyserver.key"
KEY_LOGNAME = "key_server"
KEY_LOGFILE = "key_server.log"
KEY_DB = "keyserver.db"
KEY_LEN = 2048
# -----------------------------------------------------------------------------
# MAP SERVER SETTINGS------------------------------------------------------
MAP_HOSTNAME = "localhost"
MAP_API_PORT = 5001
MAP_TLS_CERT = TLS_CERT_DIR + "mapserver.crt"
MAP_TLS_KEY = TLS_CERT_DIR + "mapserver.key"
MAP_LOGNAME = "map_server"
MAP_LOGFILE = "map_server.log"
MAP_DB = "mapserver.db"
# -----------------------------------------------------------------------------
