#!/usr/bin/env python3
"""
Provision eval methods

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
DIRECTORY = config.EVAL_DIR + "provision" + "/"
os.makedirs(DIRECTORY, exist_ok=True)
NUM_POINTS = [2000, 4000, 6000]
STORED_VALUES = 0
PAILLIER = True
TLS = True
RAM = True
log = configure_root_logger(logging.INFO, config.DATA_DIR + 'provision.log')
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


def preparation(file: str, p: int, record_file: str = None) -> None:
    """
    Prepare databases and start background tasks.
    
    :param file: Name of file to write generated points to
    :param p: Number of points
    :param record: Name of file containing record (for real-world eval only)
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

    shd.gen_points(MAP_NAME, TOOL_PROPERTIES, file, p)
    if STORED_VALUES:
        prov.full_provide_eval(MAP_NAME, TOOL_PROPERTIES, p, STORED_VALUES)


def start(file: str, com_file: str) -> subprocess.Popen:
    """
    Start producer app process and return it.

    :param file: Name of file to provide points from
    :param com_file: Communication file
    :return: Created process
    """
    cmd = ["python3", "src/producer.py", "testprod", "password",
           "-f", file, "-e", com_file]
    proc = subprocess.Popen(cmd, universal_newlines=True,
                            stderr=subprocess.PIPE)
    return proc


def main(base_filename: str, resume: bool = False,
         invalid: bool = False, real: bool = False):
    """Execute evaluation."""
    file_path = DIRECTORY + base_filename + ".csv"
    ram_path = DIRECTORY + base_filename + "_ram.csv"
    if not resume or not os.path.exists(file_path):
        if PAILLIER and not invalid:
            row_fmt = ("TIMESTAMP;"
                    "SET;"
                    "#Points;"
                    "StartTimeFile[s];"
                    "ParsedRecordTime[s];"
                    "StartTime[s];"
                    "ProviderKeyRetrievalTime[s];"
                    "ComparisonRequestTime[s];"
                    "ComparisonTime[s];"
                    "EncryptionTime[s];"
                    "ProvisionTime[s];"
                    "KSSize[Byte];MSSize[Byte];"
                    "FromKS[Byte];FromKS[Pkt];"
                    "ToKS[Byte];ToKs[Pkt];"
                    "FromMS[Byte];FromMS[Pkt];"
                    "ToMS[Byte];ToMS[Pkt];"
                    "Error")
        elif invalid:
            row_fmt = ("TIMESTAMP;"
                    "SET;"
                    "#Points;"
                    "StartTimeFile[s];"
                    "ParsedRecordTime[s];"
                    "StartTime[s];"
                    "ProviderKeyRetrievalTime[s];"
                    "EncryptionTime[s];"
                    "ProvisionTime[s];"
                    "KSSize[Byte];MSSize[Byte];"
                    "FromKS[Byte];FromKS[Pkt];"
                    "ToKS[Byte];ToKs[Pkt];"
                    "FromMS[Byte];FromMS[Pkt];"
                    "ToMS[Byte];ToMS[Pkt];"
                    "Error")
        else:
            row_fmt = ("TIMESTAMP;"
                    "SET;"
                    "#Points;"
                    "StartTimeFile[s];"
                    "ParsedRecordTime[s];"
                    "StartTime[s];"
                    "ProviderKeyRetrievalTime[s];"
                    "PlaintextProvisionTime[s];"
                    "KSSize[Byte];MSSize[Byte];"
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
    if real:
        record_file = config.WORKING_DIR + "data/real_world_record.txt"
        points = [30]

    for s in lb(range(config.SETS), "Sets", position=0):
        for p in lb(points, "Number of Points", leave=False):
            log.info("Preparing...")
            provision_file = helpers.get_temp_file() + "_provision.txt"
            preparation(provision_file, p)
            if real:
                provision_file = record_file
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

                    process = start(provision_file, com_file)
                    process.wait()

                    # Load com file
                    with open(com_file, "rb") as fd:
                        e = pickle.load(fd)
                    if e['error'] is not None:
                        raise RuntimeError(e['error'])
                    ram_usage = e['ram_usage']

                    # Kill TCPDUMP
                    helpers.kill_tcpdump()
                    for proc in measurements:
                        # Wait for termination
                        proc.wait()

                    # Get Data Amount results
                    fks_byte, fks_pkt = helpers.read_tcpstat_from_file(
                        fks_file)
                    tks_byte, tks_pkt = helpers.read_tcpstat_from_file(
                        tks_file)
                    fms_byte, fms_pkt = helpers.read_tcpstat_from_file(
                        fms_file)
                    tms_byte, tms_pkt = helpers.read_tcpstat_from_file(
                        tms_file)

                    # Get size of databases
                    ks_size = os.path.getsize(config.DATA_DIR + config.KEY_DB)
                    ms_size = os.path.getsize(config.DATA_DIR + config.MAP_DB)

                    if PAILLIER and not invalid:
                        with open(file_path, "a", encoding='utf-8') as fd:
                            row = ';'.join((
                                time.strftime('%Y-%m-%d %H:%M:%S'),
                                str(s),
                                str(p),
                                str(e['start_time_file']),
                                str(e['parsed_record_time']),
                                str(e['start_time']),
                                str(e['provider_key_retrieval_time']),
                                str(e['comparison_request_time']),
                                str(e['comparison_time']),
                                str(e['encryption_time']),
                                str(e['provision_time']),
                                str(ks_size),
                                str(ms_size),
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
                            fd.write(
                                f"{row}\n")
                    elif PAILLIER and invalid:
                        with open(file_path, "a", encoding='utf-8') as fd:
                            row = ';'.join((
                                time.strftime('%Y-%m-%d %H:%M:%S'),
                                str(s),
                                str(p),
                                str(e['start_time_file']),
                                str(e['parsed_record_time']),
                                str(e['start_time']),
                                str(e['provider_key_retrieval_time']),
                                str(e['encryption_time']),
                                str(e['plaintext_provision_time']), # plaintext only in name
                                str(ks_size),
                                str(ms_size),
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
                            fd.write(
                                f"{row}\n")
                    else:
                        with open(file_path, "a", encoding='utf-8') as fd:
                            row = ';'.join((
                                time.strftime('%Y-%m-%d %H:%M:%S'),
                                str(s),
                                str(p),
                                str(e['start_time_file']),
                                str(e['parsed_record_time']),
                                str(e['start_time']),
                                str(e['provider_key_retrieval_time']),
                                str(e['plaintext_provision_time']),
                                str(ks_size),
                                str(ms_size),
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
                            fd.write(
                                f"{row}\n")
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



def get_provision_parser() -> argparse.ArgumentParser:
    """Return argparser for provision eval."""
    parser = argparse.ArgumentParser(description="Provision Eval")
    parser.add_argument('--resume', action="store_true",
                        help="Append to file.", default=False)
    parser.add_argument('--invalid', action="store_true",
                        help="Deactivate validation.", default=False)
    parser.add_argument('--real', action="store_true",
                        help="Use real-world data.", default=False)
    parser.add_argument('-o', '--out', type=str, action='store',
                        help="Base filename WITHOUT file-ending!",
                        required=True)
    parser.add_argument('-s', '--stored', type=int, action='store',
                        help="Number of values stored per point.",
                        default=0, choices=(0,1,2,3))
    parser.add_argument('-p', "--paillier", help="Deactivate Paillier.",
                        action="store_false", default=True)
    parser.add_argument('-t', "--tls", help="Deactivate TLS.",
                        action="store_false", default=True)
    parser.add_argument('-r', "--ram", help="Deactivate RAM measurement.",
                        action="store_false", default=True)
    return parser


if __name__ == '__main__':
    if not config.EVAL:
        log.error("config.EVAL has to be True.")
        sys.exit(-1)
    parser = get_provision_parser()
    args = parser.parse_args()
    STORED_VALUES = args.stored
    PAILLIER = args.paillier
    TLS = args.tls
    RAM = args.ram
    main(args.out, args.resume, args.invalid, args.real)
