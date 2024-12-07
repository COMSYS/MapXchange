#!/usr/bin/env python3
"""
Paillier eval methods

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import argparse
import logging
import os
import sys
import time

from phe import paillier

from src.eval.shared import lb
from src.lib import config
from src.lib.logging import configure_root_logger

# Constants -------------------------------------------------------------------
DIRECTORY = config.EVAL_DIR + "paillier" + "/"
os.makedirs(DIRECTORY, exist_ok=True)
log = configure_root_logger(logging.INFO, config.DATA_DIR + 'paillier.log')
# -----------------------------------------------------------------------------


def write_header(file_path: str, reps: int, row_fmt: str):
    """Write header into csv file."""
    with open(file_path, 'w', encoding='utf-8') as fd:
        fd.write("---------------------BEGIN HEADER---------------------\n")
        fd.write(f"Key Length: {config.KEY_LEN}\n")
        fd.write(f"Sets: {config.SETS}\n")
        fd.write(f"Reps: {reps}\n")
        fd.write(f"{row_fmt}\n")
        fd.write("----------------------END HEADER----------------------\n")


def main(base_filename: str, reps: int, resume: bool = False):
    """Execute evaluation."""
    file_path = DIRECTORY + base_filename + ".csv"
    if not resume or not os.path.exists(file_path):
        row_fmt = "SET;DURATION"
        write_header(file_path, reps, row_fmt)
    public_key, private_key = paillier.generate_paillier_keypair(n_length=config.KEY_LEN)

    with open(file_path, "a", encoding='utf-8') as fd:
        fd.write("Key Generation\n")
    for s in lb(range(config.SETS), "Sets", position=0):
        start = time.monotonic()
        for r in lb(range(reps), "Repetitions", leave=False):
            paillier.generate_paillier_keypair(n_length=config.KEY_LEN)
        duration = time.monotonic() - start
        with open(file_path, "a", encoding='utf-8') as fd:
            fd.write(f"{s};{duration}\n")

    with open(file_path, "a", encoding='utf-8') as fd:
        fd.write("\nEncryption\n")
    for s in lb(range(config.SETS), "Sets", position=0):
        start = time.monotonic()
        for r in lb(range(reps), "Repetitions", leave=False):
            public_key.encrypt(13)
        duration = time.monotonic() - start
        with open(file_path, "a", encoding='utf-8') as fd:
            fd.write(f"{s};{duration}\n")

    with open(file_path, "a", encoding='utf-8') as fd:
        fd.write("\nCiphertext Extraction\n")
    for s in lb(range(config.SETS), "Sets", position=0):
        enc_13 = public_key.encrypt(13)
        start = time.monotonic()
        for r in lb(range(reps), "Repetitions", leave=False):
            enc_13.ciphertext()
        duration = time.monotonic() - start
        with open(file_path, "a", encoding='utf-8') as fd:
            fd.write(f"{s};{duration}\n")

    with open(file_path, "a", encoding='utf-8') as fd:
        fd.write("\nEncryptedNumber Generation\n")
    for s in lb(range(config.SETS), "Sets", position=0):
        ct_13 = public_key.encrypt(13).ciphertext()
        start = time.monotonic()
        for r in lb(range(reps), "Repetitions", leave=False):
            paillier.EncryptedNumber(public_key, ct_13)
        duration = time.monotonic() - start
        with open(file_path, "a", encoding='utf-8') as fd:
            fd.write(f"{s};{duration}\n")

    with open(file_path, "a", encoding='utf-8') as fd:
        fd.write("\nPlaintext Addition\n")
    for s in lb(range(config.SETS), "Sets", position=0):
        enc_13 = public_key.encrypt(13)
        start = time.monotonic()
        for r in lb(range(reps), "Repetitions", leave=False):
            enc_13 + 13
        duration = time.monotonic() - start
        with open(file_path, "a", encoding='utf-8') as fd:
            fd.write(f"{s};{duration}\n")

    with open(file_path, "a", encoding='utf-8') as fd:
        fd.write("\nCiphertext Addition\n")
    for s in lb(range(config.SETS), "Sets", position=0):
        enc_13 = public_key.encrypt(13)
        start = time.monotonic()
        for r in lb(range(reps), "Repetitions", leave=False):
            enc_13 + enc_13
        duration = time.monotonic() - start
        with open(file_path, "a", encoding='utf-8') as fd:
            fd.write(f"{s};{duration}\n")

    with open(file_path, "a", encoding='utf-8') as fd:
        fd.write("\nDecryption\n")
    for s in lb(range(config.SETS), "Sets", position=0):
        enc_13 = public_key.encrypt(13)
        start = time.monotonic()
        for r in lb(range(reps), "Repetitions", leave=False):
            private_key.decrypt(enc_13)
        duration = time.monotonic() - start
        with open(file_path, "a", encoding='utf-8') as fd:
            fd.write(f"{s};{duration}\n")


def get_paillier_parser() -> argparse.ArgumentParser:
    """Return argparser for Paillier eval."""
    parser = argparse.ArgumentParser(description="Paillier Eval")
    parser.add_argument('--resume', action="store_true",
                        help="Append to file.", default=False)
    parser.add_argument('-o', '--out', type=str, action='store',
                        help="Base filename WITHOUT file extension!",
                        required=True)
    parser.add_argument('-r', '--reps', help="Number of repetitions.",
                        default=1000, type=int)
    return parser


if __name__ == '__main__':
    parser = get_paillier_parser()
    args = parser.parse_args()
    main(args.out, args.reps, args.resume)
