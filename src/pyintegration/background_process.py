import io
import subprocess

from datetime import datetime
from typing import Optional

from .result import Result
from .utils import bytesToString
from .utils import envPrintCommands
from .utils import envPrintOutput


class BackgroundProcess:
    """
    Wraps typical Python subprocess to run in the background and collect data.

    If a process should run in the foreground, then it is better to use IntegrationTestCase.command().
    """

    def __init__(
        self,
        name: str,
        command: str,
        print_command: Optional[int] = None,
        print_output: Optional[int] = None,
    ):
        self.name = name
        self.command = command
        self.print_command = envPrintCommands(print_command)
        self.print_output = envPrintOutput(print_output)
        self.process = None
        self.startTime = None
        self.stdout = None
        self.stderr = None

    def start(self) -> None:
        """
        Starts the command in the background.
        """
        if self.print_command:
            print(self.command)

        self.stdout = io.BytesIO()
        self.stderr = io.BytesIO()
        self.startTime = datetime.now()
        self.process = subprocess.Popen(
            self.command,
            stdout=self.stdout,
            stderr=self.stderr,
            shell=False,
        )

    def cleanup(self):
        self.stdout.close()
        self.stderr.close()
        self.stdout = None
        self.stderr = None
        self.process = None
        self.startTime = None

    def stop(self) -> Optional[Result]:
        """
        Stops the process and returns the `Result`.

        It is expected the process stops cleanly. T
        """
        if not self.process:
            return None

        killCmd = f"kill {self.command}"
        if self.print_command:
            print(killCmd)

        self.process.kill()
        delta = datetime.now() - self.startTime
        out = bytesToString(self.stdout.getvalue())
        err = bytesToString(self.stderr.getvalue())

        self.cleanup()

        if self.print_output:
            print(f"Command '{self.command}' results:")
            print(out)
            print(err)

        return Result(
            return_value=0,
            command=self.command,
            timediff=delta,
            stdout=out.split("\n"),
            stderr=err.split("\n"),
        )

    def terminate(self) -> None:
        """
        Terminates the background process and catches exceptions to avoid cleanup issues.
        """
        if not self.process:
            return

        try:
            self.process.terminate()
            self.cleanup()
        except Exception as ex:
            print(f"Failed to terminate {self.name}: {ex}")
        return
