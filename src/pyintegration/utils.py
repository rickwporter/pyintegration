import os

from typing import Optional

from .constants import PYINT_PRINT_COMMANDS
from .constants import PYINT_PRINT_OUTPUT


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
