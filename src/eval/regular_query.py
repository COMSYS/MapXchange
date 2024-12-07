#!/usr/bin/env python3
"""
Regular query eval methods

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import argparse
import atexit
import contextlib
import json
import logging
import os
import pickle
import shutil
import subprocess
import sys
import time

from src.eval import shared as shd
from src.eval.shared import lb
from src.lib import config, helpers
from src.lib import db_cli as db
from src.lib.logging import configure_root_logger
from src.lib.user import UserType, ServerType
from src.producer import Producer


# Constants -------------------------------------------------------------------
SLEEP_TIME = 10
MAP_NAME = ('5rLhPSFu', 'hardened steel', 'zJcgKqGI')
TOOL_PROPERTIES = ('end mill', 4)
DIRECTORY = config.EVAL_DIR + "regular_query" + "/"
os.makedirs(DIRECTORY, exist_ok=True)
NUM_POINTS = [2000, 4000, 6000]
STORED_VALUES = 0
PAILLIER = True
TLS = True
RAM = True
log = configure_root_logger(logging.INFO, config.DATA_DIR + 'regular_query.log')
atexit.register(shutil.rmtree, config.TEMP_DIR, True)
atexit.register(shd.set_eval, config.EVAL)
atexit.register(shd.reset_config)
# -----------------------------------------------------------------------------


def write_header(file_path: str, row_fmt: str) -> None:
    """Write header into csv file."""
    with open(file_path, 'w', encoding='utf-8') as fd:
        fd.write("---------------------BEGIN HEADER---------------------\n")
        fd.write(f"Stored Values: {STORED_VALUES}\n")
        fd.write(f"Paillier Status: {PAILLIER}\n")
        fd.write(f"TLS Status: {TLS}\n")
        fd.write(f"RAM Status: {RAM}\n")
        fd.write(f"Key Length: {config.KEY_LEN}\n")
        fd.write(f"Sets: {config.SETS}\n")
        fd.write(f"Interval of RAM measurements: {config.RAM_INTERVAL}s\n")
        fd.write("\n")
        fd.write("All times in seconds! Timer is monotonic clock and starts "
                 "with 'StartTime'. Only differences are meaningful.\n")
        fd.write(f"{row_fmt}\n")
        fd.write("----------------------END HEADER----------------------\n")


def kill_bg_servers() -> None:
    """Kill old processes if running"""
    subprocess.run(["tmux", "kill-session", "-t", "eval"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


atexit.register(kill_bg_servers)


def preparation(p: int, real: bool = False) -> None:
    """
    Prepare databases and start background tasks.

    :param p: Number of points
    """
    # Kill old processes if running
    kill_bg_servers()
    time.sleep(SLEEP_TIME)

    data_dir = config.DATA_DIR

    log.info("Removing Databases.")
    with contextlib.suppress(FileNotFoundError):
        # Remove Databases
        os.remove(data_dir + config.KEY_DB)
        os.remove(data_dir + config.MAP_DB)

    # Add User
    log.info("Prepare User DB.")
    db.main(UserType.Producer, ['testprod', 'password', '-a'], no_print=True)
    db.main(UserType.Producer, ['pastprov', 'password', '-a'], no_print=True)

    log.info("Starting Background Servers.")
    subprocess.run([f"{config.WORKING_DIR}src/startServers.sh", "eval"])
    time.sleep(SLEEP_TIME)

    # Create provider
    prov = Producer('pastprov')
    prov.set_password('password')

    # Check that servers are really online
    while True:
        try:
            # Check Key Server
            prov.get_token(ServerType.KeyServer)
            # Check Map Server
            prov.get_token(ServerType.MapServer)
            # Success
            break
        except Exception as e:
            log.error(f"Server not up yet. Error: {str(e)}")
            kill_bg_servers()
            time.sleep(SLEEP_TIME)
            subprocess.run([f"{config.WORKING_DIR}src/startServers.sh", "eval"])
            time.sleep(2 * SLEEP_TIME)

    if real:
        temp_file = helpers.get_temp_file() + '_temp.pyc'
        record_file = config.WORKING_DIR + "data/real_world_record.txt"
        cmd = ["python3", "src/producer.py", "pastprov", "password",
               "-f", record_file, "-e", temp_file]
        provision = subprocess.Popen(cmd, universal_newlines=True,
                                     stderr=subprocess.PIPE)
        provision.wait()
    else:
        prov.full_provide_eval(MAP_NAME, TOOL_PROPERTIES, p, STORED_VALUES)


def start(com_file: str, real: bool = False) -> subprocess.Popen:
    """Start a client App process and return it."""
    cmd = ["python3", "src/producer.py", "testprod", "password",
           "-m", f"{MAP_NAME}", "-e", com_file]
    if real:
        map_name = ('DMU 65 monoBLOCK', 'steel', 'Fraisa p8400610')
        cmd = ["python3", "src/producer.py", "testprod", "password",
               "-m", f"{map_name}", "-e", com_file]
    if config.DEBUG:
        cmd.append('-vv')
    proc = subprocess.Popen(cmd, universal_newlines=True,
                            stderr=subprocess.PIPE)
    return proc


def main(base_filename: str, resume: bool = False, full: bool = False,
         invalid: bool = False, real: bool = False):
    """Execute evaluation."""
    file_path = DIRECTORY + base_filename + ".csv"
    ram_path = DIRECTORY + base_filename + '_ram.csv'
    if not resume or not os.path.exists(file_path):
        if PAILLIER and not invalid:
            row_fmt = ("TIMESTAMP;"
                    "SET;"
                    "#Points;"
                    "StartTime[s];"
                    "ClientKeyRetrievalTime[s];"
                    "ComparisonRequestTime[s];"
                    "ComparisonTime[s];"
                    "PointRetrievalTime[s];"
                    "PointDecryptionTime[s];"
                    "FromKS[Byte];FromKS[Pkt];"
                    "ToKS[Byte];ToKs[Pkt];"
                    "FromMS[Byte];FromMS[Pkt];"
                    "ToMS[Byte];ToMS[Pkt];"
                    "Error")
        elif invalid:
            row_fmt = ("TIMESTAMP;"
                    "SET;"
                    "#Points;"
                    "StartTime[s];"
                    "ClientKeyRetrievalTime[s];"
                    "PointRetrievalTime[s];"
                    "PointDecryptionTime[s];"
                    "FromKS[Byte];FromKS[Pkt];"
                    "ToKS[Byte];ToKs[Pkt];"
                    "FromMS[Byte];FromMS[Pkt];"
                    "ToMS[Byte];ToMS[Pkt];"
                    "Error")
        else:
            row_fmt = ("TIMESTAMP;"
                    "SET;"
                    "#Points;"
                    "StartTime[s];"
                    "ClientKeyRetrievalTime[s];"
                    "PlaintextPointRetrievalTime[s];"
                    "FromKS[Byte];FromKS[Pkt];"
                    "ToKS[Byte];ToKs[Pkt];"
                    "FromMS[Byte];FromMS[Pkt];"
                    "ToMS[Byte];ToMS[Pkt];"
                    "Error")
        write_header(file_path, row_fmt)
        if RAM:
            row_fmt = "TIMESTAMP;SET;#Points;json.dumps(ram_usage)"
            write_header(ram_path, row_fmt)
    shd.set_paillier(PAILLIER)
    shd.set_tls(TLS)
    shd.set_ram(RAM)
    points = NUM_POINTS
    if invalid:
        shd.set_valid(False)
        points = [2000, 4000, 6000]

    if full or real:
        p = config.MAP_SIZE
        if real:
            p = 30
        log.info("Preparing...")
        preparation(p, real)
        for s in lb(range(config.SETS), "Sets", position=0):
            success = False
            while not success:
                process = None
                com_file = helpers.get_temp_file() + '_comfile.pyc'
                e = None
                os.makedirs(config.TEMP_DIR, exist_ok=True)
                try:
                    error = ""
                    tks, tks_file = helpers.start_trans_measurement(
                        config.KEY_API_PORT, direction="dst", sleep=False
                    )
                    fks, fks_file = helpers.start_trans_measurement(
                        config.KEY_API_PORT, direction="src", sleep=False
                    )
                    tms, tms_file = helpers.start_trans_measurement(
                        config.MAP_API_PORT, direction="dst", sleep=False
                    )
                    fms, fms_file = helpers.start_trans_measurement(
                        config.MAP_API_PORT, direction="src", sleep=False
                    )
                    measurements = [tks, fks, tms, fms]
                    time.sleep(0.5)

                    process = start(com_file, real)
                    process.wait()

                    with open(com_file, "rb") as fd:
                        e = pickle.load(fd)
                    if e['result'] is None:
                        raise RuntimeError(e['error'])
                    ram_usage = e['ram_usage']

                    helpers.kill_tcpdump()
                    for proc in measurements:
                        proc.wait(30)

                    fks_byte, fks_pkt = helpers.read_tcpstat_from_file(
                        fks_file)
                    tks_byte, tks_pkt = helpers.read_tcpstat_from_file(
                        tks_file)
                    fms_byte, fms_pkt = helpers.read_tcpstat_from_file(
                        fms_file)
                    tms_byte, tms_pkt = helpers.read_tcpstat_from_file(
                        tms_file)

                    if PAILLIER and not invalid:
                        with open(file_path, "a", encoding='utf-8') as fd:
                            row = ";".join((
                                time.strftime('%Y-%m-%d %H:%M:%S'),
                                str(s),
                                str(p),
                                str(e['start_time']),
                                str(e['client_key_retrieval_time']),
                                str(e['comparison_request_time']),
                                str(e['comparison_time']),
                                str(e['point_retrieval_time']),
                                str(e['point_decryption_time']),
                                str(fks_byte),
                                str(fks_pkt),
                                str(tks_byte),
                                str(tks_pkt),
                                str(fms_byte),
                                str(fms_pkt),
                                str(tms_byte),
                                str(tms_pkt),
                                error
                            ))
                            fd.write(f"{row}\n")
                    elif PAILLIER and invalid:
                        with open(file_path, "a", encoding='utf-8') as fd:
                            row = ";".join((
                                time.strftime('%Y-%m-%d %H:%M:%S'),
                                str(s),
                                str(p),
                                str(e['start_time']),
                                str(e['client_key_retrieval_time']),
                                str(e['plaintext_point_retrieval_time']),
                                str(e['point_decryption_time']),
                                str(fks_byte),
                                str(fks_pkt),
                                str(tks_byte),
                                str(tks_pkt),
                                str(fms_byte),
                                str(fms_pkt),
                                str(tms_byte),
                                str(tms_pkt),
                                error
                            ))
                            fd.write(f"{row}\n")
                    else:
                        with open(file_path, "a", encoding='utf-8') as fd:
                            row = ";".join((
                                time.strftime('%Y-%m-%d %H:%M:%S'),
                                str(s),
                                str(p),
                                str(e['start_time']),
                                str(e['client_key_retrieval_time']),
                                str(e['plaintext_point_retrieval_time']),
                                str(fks_byte),
                                str(fks_pkt),
                                str(tks_byte),
                                str(tks_pkt),
                                str(fms_byte),
                                str(fms_pkt),
                                str(tms_byte),
                                str(tms_pkt),
                                error
                            ))
                            fd.write(f"{row}\n")
                    if RAM:
                        with open(ram_path, "a", encoding='utf-8') as fd:
                            fd.write(
                                ';'.join(
                                    (
                                        time.strftime('%Y-%m-%d %H:%M:%S'),
                                        str(s),
                                        str(p),
                                        json.dumps(ram_usage)
                                    )
                                ) + '\n'
                            )
                    success = True
                except Exception as e:
                    log.exception(str(e))
                    success = False
                finally:
                    if process is not None:
                        process.terminate()
                        try:
                            process.wait(5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                    helpers.kill_tcpdump()
            shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
        return

    for s in lb(range(config.SETS), "Sets", position=0):
        for p in lb(points, "Number of Points", leave=False):
            log.info("Preparing...")
            preparation(p)
            success = False
            while not success:
                process = None
                com_file = helpers.get_temp_file() + '_comfile.pyc'
                e = None
                # May be deleted by clean-up of prev. round
                os.makedirs(config.TEMP_DIR, exist_ok=True)
                try:
                    error = ""
                    # Start data measurements
                    tks, tks_file = helpers.start_trans_measurement(
                        config.KEY_API_PORT, direction="dst", sleep=False
                    )
                    fks, fks_file = helpers.start_trans_measurement(
                        config.KEY_API_PORT, direction="src", sleep=False
                    )
                    tms, tms_file = helpers.start_trans_measurement(
                        config.MAP_API_PORT, direction="dst", sleep=False
                    )
                    fms, fms_file = helpers.start_trans_measurement(
                        config.MAP_API_PORT, direction="src", sleep=False
                    )
                    measurements = [tks, fks, tms, fms]
                    time.sleep(0.5)

                    process = start(com_file)
                    process.wait()

                    # Load com file
                    with open(com_file, "rb") as fd:
                        e = pickle.load(fd)
                    if e['result'] is None:
                        # full_retrieve did not terminate
                        raise RuntimeError(e['error'])
                    ram_usage = e['ram_usage']

                    # Kill TCPDUMP
                    helpers.kill_tcpdump()
                    for proc in measurements:
                        # Wait for termination
                        proc.wait(30)

                    # Get Data Amount results
                    fks_byte, fks_pkt = helpers.read_tcpstat_from_file(
                        fks_file)
                    tks_byte, tks_pkt = helpers.read_tcpstat_from_file(
                        tks_file)
                    fms_byte, fms_pkt = helpers.read_tcpstat_from_file(
                        fms_file)
                    tms_byte, tms_pkt = helpers.read_tcpstat_from_file(
                        tms_file)

                    if PAILLIER and not invalid:
                        with open(file_path, "a", encoding='utf-8') as fd:
                            row = ";".join((
                                time.strftime('%Y-%m-%d %H:%M:%S'),
                                str(s),
                                str(p),
                                str(e['start_time']),
                                str(e['client_key_retrieval_time']),
                                str(e['comparison_request_time']),
                                str(e['comparison_time']),
                                str(e['point_retrieval_time']),
                                str(e['point_decryption_time']),
                                str(fks_byte),
                                str(fks_pkt),
                                str(tks_byte),
                                str(tks_pkt),
                                str(fms_byte),
                                str(fms_pkt),
                                str(tms_byte),
                                str(tms_pkt),
                                error
                            ))
                            fd.write(f"{row}\n")
                    elif PAILLIER and invalid:
                        with open(file_path, "a", encoding='utf-8') as fd:
                            row = ";".join((
                                time.strftime('%Y-%m-%d %H:%M:%S'),
                                str(s),
                                str(p),
                                str(e['start_time']),
                                str(e['client_key_retrieval_time']),
                                str(e['plaintext_point_retrieval_time']),
                                str(e['point_decryption_time']),
                                str(fks_byte),
                                str(fks_pkt),
                                str(tks_byte),
                                str(tks_pkt),
                                str(fms_byte),
                                str(fms_pkt),
                                str(tms_byte),
                                str(tms_pkt),
                                error
                            ))
                            fd.write(f"{row}\n")
                    else:
                        with open(file_path, "a", encoding='utf-8') as fd:
                            row = ";".join((
                                time.strftime('%Y-%m-%d %H:%M:%S'),
                                str(s),
                                str(p),
                                str(e['start_time']),
                                str(e['client_key_retrieval_time']),
                                str(e['plaintext_point_retrieval_time']),
                                str(fks_byte),
                                str(fks_pkt),
                                str(tks_byte),
                                str(tks_pkt),
                                str(fms_byte),
                                str(fms_pkt),
                                str(tms_byte),
                                str(tms_pkt),
                                error
                            ))
                            fd.write(f"{row}\n")
                    if RAM:
                        with open(ram_path, "a", encoding='utf-8') as fd:
                            fd.write(
                                ';'.join(
                                    (
                                        time.strftime('%Y-%m-%d %H:%M:%S'),
                                        str(s),
                                        str(p),
                                        json.dumps(ram_usage)
                                    )
                                ) + '\n'
                            )
                    success = True
                except Exception as e:
                    log.exception(str(e))
                    success = False
                finally:
                    # Clean Up
                    if process is not None:
                        process.terminate()
                        try:
                            process.wait(5)
                        except subprocess.TimeoutExpired:
                            # Terminate was not enough
                            process.kill()
                    # Kill TCPDUMP
                    helpers.kill_tcpdump()
            # Remove Tempfiles
            shutil.rmtree(config.TEMP_DIR, ignore_errors=True)


def get_regular_query_parser() -> argparse.ArgumentParser:
    """Return argparser for regular_query eval."""
    parser = argparse.ArgumentParser(description="Regular Query Eval")
    parser.add_argument('--resume', action="store_true",
                        help="Append to file.", default=False)
    parser.add_argument('--full', action="store_true",
                        help="Use full map.", default=False)
    parser.add_argument('--invalid', action="store_true",
                        help="Deactivate validation.", default=False)
    parser.add_argument('--real', action="store_true",
                        help="Use real-world data.", default=False)
    parser.add_argument('-o', '--out', type=str, action='store',
                        help="Base filename WITHOUT file-ending!",
                        required=True)
    parser.add_argument('-s', '--stored', type=int, action='store',
                        help="Number of values stored per point.",
                        default=1, choices=(1,2,3))
    parser.add_argument('-p', "--paillier", help="Deactivate Paillier.",
                        action="store_false", default=True)
    parser.add_argument('-t', "--tls", help="Deactivate TLS.",
                        action="store_false", default=True)
    parser.add_argument('-r', "--ram", help="Deactivate RAM measurement.",
                        action="store_false", default=True)
    return parser


if __name__ == '__main__':
    shd.set_eval(True)
    parser = get_regular_query_parser()
    args = parser.parse_args()
    STORED_VALUES = args.stored
    PAILLIER = args.paillier
    TLS = args.tls
    RAM = args.ram
    main(args.out, args.resume, args.full, args.invalid, args.real)
