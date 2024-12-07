"""
Shared eval methods

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import logging
import secrets
import subprocess
from collections.abc import Iterable

from tqdm import tqdm

from src.lib import config


log = logging.getLogger(__name__)


def reset_config() -> None:
    """Reset config file."""
    subprocess.run(['git', 'checkout', '-f', 'src/lib/config.py'])


def set_config(variable: str, v: bool) -> None:
    """Set chosen variable in config file to given value."""
    with open(config.WORKING_DIR + "src/lib/config.py", "r", encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if f"{variable} =" in line:
            lines[i] = f"{variable} = {str(v)}\n"
    # Overwrite
    with open(config.WORKING_DIR + "src/lib/config.py", "w", encoding='utf-8') as f:
        f.writelines(lines)


def set_eval(v: bool) -> None:
    """Set evaluation mode."""
    set_config("EVAL", v)


def set_paillier(v: bool) -> None:
    """Set encryption of feed rate and usage data."""
    set_config("USE_PAILLIER", v)


def set_tls(v: bool) -> None:
    """Set encryption of HTTP payload data."""
    set_config("USE_TLS", v)


def set_ram(v: bool) -> None:
    """Set measurement of RAM usage."""
    set_config("MEASURE_RAM", v)


def set_valid(v: bool) -> None:
    """Set validation."""
    set_config("VALID", v)


def lb(o, *args, **kwargs):
    """Return a tqdm object if there is more than one element."""
    if ((isinstance(o, list) or isinstance(o, tuple)) and len(o) == 1):
        return o
    elif isinstance(o, Iterable):
        return tqdm(o, *args, **kwargs)
    else:
        return [o]


def gen_points(map_name: tuple[str, str, str], tool_properties: tuple[str, int],
               file: str, p=config.MAP_SIZE) -> None:
    """
    Generate p points and store them to specified file as record
    with given map name and tool properties.

    :param file: Name of file to write points to
    :param p: Number of points
    """
    ap_ae = [(ap+1, ae+1)
             for ap in range(config.AP_PRECISION)
             for ae in range(config.AE_PRECISION)]
    ap_ae = ap_ae[:p]
    points = [(ap, ae,
              secrets.randbelow(config.FZ_PRECISION+1),
              secrets.randbelow(config.USAGE_PRECISION+1))
              for ap, ae in ap_ae]
    mato = list(map_name)
    mato.extend(list(tool_properties))
    record = (mato, points[:(p+1)])
    with open(file, "w", encoding='utf-8') as fd:
        fd.write(f"{str(record)}\n")
