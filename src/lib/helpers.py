"""
Miscellaneous helper functions

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import base64
import logging
import re
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from io import StringIO

import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np

import src.lib.config as config

log: logging.Logger = logging.getLogger(__name__)


class Record:
    """Record containing multiple points for one map"""

    def __init__(self, map_name: tuple[str, str, str],
             tool_properties: tuple[str, int],
             points: list[tuple[int, int, int, int]]) -> None:
        """Create record."""
        self.map_name = map_name
        self.tool_properties = tool_properties
        self.points = points

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Record):
            return False
        return (self.map_name == other.map_name and
                self.tool_properties == other.tool_properties and
                self.points == other.points)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)


def get_temp_file() -> str:
    """Generate random tempfile and create directory if none exist."""
    return config.TEMP_DIR + str(uuid.uuid4())


def start_trans_measurement(port: int, protocol: str = None, direction: str = "both",
                            sleep: bool = True, file=None
                            ) -> tuple[subprocess.Popen, str]:  # pragma no cover
    """
    Measure transmitted data on port.

    :param file: File to write pcap to. If undef. a tempfile is used
    :param sleep: Attention: Short manual sleep required (0.01s)
    :param port: Port to listen on
    :param protocol: [OPTIONAL] Protocol to listen for, otherwise all
    :param direction: [OPTIONAL] € {src, dst}
    :return: Popen object that can be given to stop_trans_measurement
    """
    if file is None:
        file = get_temp_file()
    cmd = ['sudo', 'tcpdump', '-i', 'lo', '-w', file, '-U',
           '--immediate-mode'] # -U is no buffer
    if direction != 'both':
        cmd.append(direction)
    cmd.extend(['port', str(port)])
    if protocol is not None:
        cmd.append('and')
        cmd.append(str(protocol))
    log.debug(f"Starting transmission measurement: f{str(cmd)}")
    s = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    if sleep:
        time.sleep(0.01)
    return s, file


def read_tcpstat_from_file(file: str) -> tuple[int, int]:  # pragma no cover
    """
    Read transmitted bytes and packets from pcap file.
    
    :param file:
    :return:
    """
    out_fmt = 'B=%N:p=%n'
    s = subprocess.run(["tcpstat", "-r", file, "-o", f"{out_fmt}", "-1"],
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    out = s.stdout
    try:
        m = re.search(r"B=(\d+):p=(\d+)", str(out))
        b = int(m.group(1))
        packets = int(m.group(2))
    except AttributeError as exc:  # pragma no cover
        raise ValueError("No valid output of TCPSTAT.") from exc
    if b == 0:
        raise RuntimeError("Capturing Packets failed.")
    return b, packets


def kill_tcpdump() -> None:  # pragma no cover
    """Kill all TCPDUMP processes with SIGINT signal."""
    # Kill tcpdump gracefully
    subprocess.run(["sudo", "killall", "-s", "2", "tcpdump"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def reset_tc() -> None:  # pragma no cover
    """
    Remove artifical latency and bandwidth limits
    from all ports. [Linux only]
    """
    log.debug("Reset Latency and Rate for all ports.")
    s = subprocess.Popen(["tcdel", "lo", "--all"],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = s.communicate()
    if err != b'':
        log.warning(str(err))


def set_tc(latency:int, bandwidth: int) -> None:  # pragma no cover
    """
    Add latency and/or limit bandwidth for all ports. [Linux only]

    :param latency: Latency in ms
    :param bandwidth: Bandwidth in kbit/s
    """
    if not bandwidth:
        log.debug(f"Set latency of {latency}ms for all ports.")
        s = subprocess.Popen(
            ["tcset", "lo", "--delay", f"{latency}ms"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = s.communicate()
        if err != b'':
            log.warning(str(err))
    elif not latency:
        log.debug(f"Set bandwidth of {bandwidth}kbit/s for all ports.")
        s = subprocess.Popen(
            ["tcset", "lo", "--rate", f"{bandwidth}kbit/s"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = s.communicate()
        if err != b'':
            log.warning(str(err))
    else:
        log.debug(f"Set latency of {latency}ms and "
                  f"bandwidth of {bandwidth}kbit/s for all ports.")
        s = subprocess.Popen(
            ["tcset", "lo", "--delay", f"{latency}ms",
             "--rate", f"{bandwidth}kbit/s"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = s.communicate()
        if err != b'':
            log.warning(str(err))


def to_base64(x: int) -> str:
    """
    Convert int to Base64 encoded string for storage and transmission.

    :param x: The int to encode
    :return: Base64 encoded string
    """
    b = x.to_bytes((x.bit_length() + 7) // 8, 'big')
    return base64.b64encode(b).decode()


def from_base64(b64: str) -> bytes:
    """
    Convert Base64 encoded string back to int.

    :param b64: Base64 encoded string
    :return: The decoded int
    """
    b = base64.b64decode(b64.encode())
    return int.from_bytes(b, 'big')


@contextmanager
def captured_output():
    """Capture outputs to StdOut and StdErr."""
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def parse_record(string: str) -> Record:
    """
    Convert string representation of record into Record.
    
    :param string: Line generated by src.record_generator
    :return: Record object
    """
    r_list = string.replace(
        '(', '').replace(
        '[', '').replace(
        ']', '').replace(
        ')', '').replace(
        '\'', '').strip('\n').split(', ')

    map_name = tuple(r_list[0:3])
    tool_properties = (r_list[3], int(r_list[4]))
    points = [tuple(int(r) for r in r_list[i:i + 4])
               for i in range(5, len(r_list), 4)]
    return Record(map_name, tool_properties, points)


def generate_auth_header(user: str, token: str) -> list[tuple[str, str]]:
    """Generate valid HTTPBasicAuth Header for given username and password."""
    b64: bytes = base64.b64encode(bytes(f"{user}:{token}",
                                        encoding='UTF-8'))
    return [('Authorization', f'Basic {b64.decode()}')]


def print_time(t: float) -> str:
    """
    Convert time to human-readable representation.

    :param t: Time in seconds
    :return: String representation
    """
    t = t * 1000  # to ms
    if t < 1000:
        return f"{round(t, 2)}ms"
    elif t < 60000:
        return f"{round(t / 1000, 2)}s"
    elif t < 3600000:
        sec = t / 1000
        minute = int(sec // 60)
        sec = sec % 60
        return f"{minute}min {round(sec, 2)}s"
    else:
        sec = t / 1000
        minute = sec // 60
        sec = sec % 60
        h = int(minute // 60)
        minute = int(minute % 60)
        return f"{h}h {minute}min {round(sec, 2)}s"


def plot_ap_ae_fz(ap: list[int], ae: list[int], fz: list[int]) -> None:
    """
    Plot cutting depth, cutting width, feed per tooth.
    
    :param ap: List of cutting depth values
    :param ae: List of cutting width values
    :param fz: List of feed per tooth values
    """
    ap_arr = np.array(ap)
    ae_arr = np.array(ae)
    fz_arr = np.array(fz)
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    surf = ax.plot_trisurf(ap_arr, ae_arr, fz_arr,
                           cmap=cm.jet, linewidth=0.1)
    fig.colorbar(surf, shrink=0.5, aspect=5)
    ax.scatter(ap_arr, ae_arr, fz_arr)
    ax.set_xlabel('$a_{e}$ [mm]')
    ax.set_ylabel('$a_{p}$ [mm]')
    ax.set_zlabel('$f_{z}$ [mm/tooth]')
    plt.show()

def usage_histogram(ap: list[int], ae: list[int], usage: list[int]) -> None:
    """
    Plot cutting depth, cutting width, usage data.
    
    :param ap: List of cutting depth values
    :param ae: List of cutting width values
    :param usage: List of usage data values
    """
    ap_arr = np.array(ap) - 0.25
    ae_arr = np.array(ae) - 0.25
    usage_arr = np.array(usage)
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    dp = np.ones(len(ap)) * 0.5
    de = np.ones(len(ae)) * 0.5
    ax.bar3d(ap_arr, ae_arr, 0, dp, de, usage_arr)
    ax.set_xlabel('$a_{e}$ [mm]')
    ax.set_ylabel('$a_{p}$ [mm]')
    ax.set_zlabel('usage [?mm?]')
    plt.show()
