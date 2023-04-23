import os
import socket

from typing import Optional

from .constants import PYINT_PRINT_COMMANDS
from .constants import PYINT_PRINT_OUTPUT


def bytesToString(bytes: Optional[bytes]) -> str:
    """
    Converts `bytes` to a string. The string will be empty if there are no
    bytes (easier downstream processing). It also ignores errors, and removes
    the `\r` from the logs (for easier cross-platform interop).
    """
    if not bytes:
        return ""
    return bytes.decode("us-ascii", errors="ignore").replace("\r", "")


def envPrintCommands(print_cmd: Optional[int] = None) -> int:
    """
    Resolves 'print_command' to an integer at runtime based on the input and environment variable.
    """
    if print_cmd is not None:
        return print_cmd
    return int(os.environ.get(PYINT_PRINT_COMMANDS, "0"))


def envPrintOutput(print_out: Optional[int] = None) -> int:
    """
    Resolves 'print_output' to an integer at runtime based on the input and environment variable.
    """
    if print_out is not None:
        return print_out
    return int(os.environ.get(PYINT_PRINT_OUTPUT, "0"))


def getLocalIp() -> str:
    """
    Gets a localhost IP address (not on docker network)
    """
    hostname = socket.getfqdn()
    try:
        return socket.gethostbyname_ex(hostname)[2][0]
    except socket.gaierror as ex:
        # reraise the error in this case
        if "." in hostname:
            raise ex

        # on Mac, we canget here when not hooked into DNS
        return socket.gethostbyname_ex(hostname + ".local")[2][0]
