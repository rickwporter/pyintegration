import os

from typing import Optional

from .constants import PYINT_PRINT_COMMANDS
from .constants import PYINT_PRINT_OUTPUT

def env_print_commands(print_cmd: Optional[int] = None) -> int:
    if print_cmd is not None:
        return print_cmd
    return int(os.environ.get(PYINT_PRINT_COMMANDS, "0"))

def env_print_output(print_out: Optional[int] = None) -> int:
    if print_out is not None:
        return print_out
    return int(os.environ.get(PYINT_PRINT_OUTPUT, "0"))
