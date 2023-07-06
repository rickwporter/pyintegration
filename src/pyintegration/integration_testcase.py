import os
import requests
import subprocess
import unittest

from datetime import datetime
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Type

from .background_process import BackgroundProcess
from .container import Container
from .container import waitForReady
from .constants import DEFAULT_CONTAINER_READY_TIMEOUT
from .constants import DEFAULT_CONTAINER_POLL_MAX
from .constants import DEFAULT_REQUEST_TIMEOUT
from .constants import PYINT_CAPTURE
from .constants import PYINT_JOB_ID
from .constants import PYINT_KNOWN_ISSUES
from .result import Result
from .utils import envPrintCommands
from .utils import envPrintOutput


def find_by_prop(entries: List[Dict], prop_name: str, prop_value: str) -> List[Dict]:
    return [e for e in entries if e.get(prop_name, None) == prop_value]


def missing_any(env_var_names: List[str]) -> bool:
    return not all([os.environ.get(x) for x in env_var_names])


# decorator to mark a test as a known issue
def skip_known_issue(msg: str):
    return unittest.skipUnless(os.environ.get(PYINT_KNOWN_ISSUES), f"Known issue: {msg}")


class IntegrationTestCase(unittest.TestCase):
    """
    This extends the unittest.TestCase to add some basic functions
    """

    def __init__(self, *args, **kwargs):
        self.print_commands: int = envPrintCommands()
        self.print_output: int = envPrintOutput()
        self.capture_scheme: Optional[str] = os.environ.get(PYINT_CAPTURE)
        self.job_id: Optional[int] = os.environ.get(PYINT_JOB_ID)
        self._capture_data: List[str] = None
        self.capture_separator: str = "**************************"
        self._filenames: List[str] = None
        self._containers: List[Container] = None
        self._processes: List[BackgroundProcess] = None
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def setUp(self) -> None:
        # collects logs to display when/if the test case fails
        self._capture_data = list()
        self._filenames = set()
        self._containers = list()
        self._processes = list()
        super().setUp()

    def tearDown(self) -> None:
        # capture data according to schema
        if (
            self.capture_scheme == "all"
            or (self.capture_scheme == "success" and self.isSuccessful())
            or (not self.isSuccessful())
        ):
            self.writeCaptureData()

        # remove any added files
        for fname in self._filenames:
            os.remove(fname)

        self._containers.reverse()
        for c in self._containers:
            c.terminate()

        self._processes.reverse()
        for p in self._processes:
            p.terminate()

        super().tearDown()

    def writeCaptureData(self) -> None:
        if not self._capture_data:
            return

        filename = f"{self._testMethodName}_commands{'_' + self.job_id if self.job_id else ''}.log"
        try:
            file = open(filename, "w")
            file.write('\n'.join(self._capture_data))
            file.close()
        except Exception as ex:
            print(f"Failed to write captured data to '{filename}': {ex}")

    def isSuccessful(self) -> bool:
        # Python 3.4 - 3.10
        if hasattr(self._outcome, "errors"):
            result = self.defaultTestResult()
            self._feedErrorsToResult(result, self._outcome.errors)
        # Python 3.11+
        else:
            result = self._outcome.result
        success = all(test != self for test, _ in result.errors + result.failures)
        return success

    def writeFile(self, filename: str, content: str) -> None:
        """
        Utility to open set the filename content, and save the name in the list
        for deletion.
        """
        self._filenames.add(filename)
        file = open(filename, "w")
        file.write(content)
        file.close()

    def deleteFile(self, filename):
        self._filenames.remove(filename)
        os.remove(filename)

    def addContainer(self, container: Container) -> None:
        self._containers.append(container)

    def getContainer(self, partial_name: str) -> Optional[Container]:
        for c in self._containers:
            if partial_name in c.name:
                return c
        return None

    def getContainerClass(self, type: Type) -> List[Container]:
        return [_ for _ in self._containers if isinstance(_, type)]

    def addProcess(self, process: BackgroundProcess) -> None:
        self._processes.append(process)

    def getProcess(self, partial_name: str) -> Optional[BackgroundProcess]:
        for p in self._processes:
            if partial_name in p.name:
                return p
        return None

    def fullName(self, name: str) -> str:
        """
        Adds the JOB_ID to the name if present, so multiple tests can run simultaneously.
        """
        if not self.job_id:
            return name
        return name + "-" + self.job_id

    def assertResultSuccess(self, result: Result, success_msg: Optional[str] = None):
        """
        This is a convenience method to check the return code, and error output.
        """
        # check the error message is empty first, since it gives the most info about a failure
        self.assertEqual(result.err(), "")
        self.assertEqual(result.return_value, 0)
        if success_msg:
            self.assertIn(success_msg, result.out())

    def assertResultWarning(self, result: Result, warn_msg: str):
        """
        This is a convenience method to check for successful CLI commands that emit a (partial) warning message
        """
        # check the message first, since it is more telling when the command fails
        self.assertIn(warn_msg, result.err())
        self.assertEqual(result.return_value, 0)

    def assertResultError(self, result: Result, err_msg: str):
        """
        This is a convenience method to check for failed CLI commands with a specific (partial) error message
        """
        self.assertIn(err_msg, result.err())
        self.assertNotEqual(result.return_value, 0)

    def assertResultIn(self, result: Result, needle: str):
        """
        This is a convenience method to check for the needle in either stdout or stderr
        """
        self.assertIn(needle, result.all())

    def logResult(self, result: Result) -> None:
        """
        Puts the data from `result` into the _capture_data.

        It does NOT immediately get written to a file! That depends on the test result and
        the `capture_schema` setting.
        """
        self._capture_data.append(f"{self.capture_separator} Command: {result.command}")
        self._capture_data.append(f"Return: {result.return_value}")
        if result.timediff:
            self._capture_data.append(f"Time: {result.timediff.total_seconds()}")
        if result.stdout:
            self._capture_data.extend(result.stdout)
        if result.stderr:
            self._capture_data.extend(result.stderr)
        # make sure we have a blank line at the end
        if self._capture_data[-1]:
            self._capture_data.append("")
        return

    def command(self, cmd: str, env: Optional[Dict[str, str]] = None) -> Result:
        """
        Runs the provided command, prints gozintas/gozoutas according to log settings,
        and captures the data from the command.
        """
        # WARNING: DOS prompt does not like the single quotes, so use double
        cmd = cmd.replace("'", '"')

        if self.print_commands:
            print(cmd)

        start = datetime.now()
        process = subprocess.run(cmd, env=env, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        delta = datetime.now() - start
        result = Result(
            return_value=process.returncode,
            stdout=process.stdout.decode("us-ascii", errors="ignore").replace("\r", "").split("\n"),
            stderr=process.stderr.decode("us-ascii", errors="ignore").replace("\r", "").split("\n"),
            timediff=delta,
            command=cmd,
        )

        # Log outputs
        if self.print_output:
            if result.stdout:
                print("\n".join(result.stdout))
            if result.stderr:
                print("\n".join(result.stderr))

        self.logResult(result)
        return result

    def curl(
        self,
        method: str,
        url: str,
        timeout: float = DEFAULT_REQUEST_TIMEOUT,
        body: Optional[Any] = None,
        filter_func: Optional[Callable[[str], bool]] = None,
        filter_desc: Optional[str] = None,
    ):
        command = f"curl -X {method} {url} {filter_desc or ''}"
        if self.print_commands:
            print(command)

        start = datetime.now()
        try:
            resp = requests.request(method, url, data=body, timeout=timeout)
            delta = datetime.now() - start
            rv = 0 if resp.ok else resp.status_code
            stdout = [""] if not resp.text else resp.text.split('\n')
            stderr = []
        except Exception as ex:
            delta = datetime.now() - start
            rv = -1
            stdout = []
            stderr = str(ex).split('\n')

        if filter_func and stdout:
            stdout = [_ for _ in stdout if filter_func(_)]

        if self.print_output:
            print('\n'.join(stdout))

        return Result(
            command=command,
            return_value=rv,
            timediff=delta,
            stdout=stdout,
            stderr=stderr
        )

    def waitForReady(
        self,
        containers: List[Container],
        max_wait_seconds: float = DEFAULT_CONTAINER_READY_TIMEOUT,
        max_poll_seconds: float = DEFAULT_CONTAINER_POLL_MAX,
        message: Optional[str] = None,
    ) -> None:
        unready = waitForReady(
            containers, max_wait_seconds=max_wait_seconds, max_poll_seconds=max_poll_seconds, message=message
        )
        if unready:
            if self.capture_scheme != "none":
                self.writeCaptureData()
            self.tearDown()
            names = [_.name for _ in unready]
            msg = message if message else f"{len(containers)} containers to be ready"
            error_msg = f"Failed waiting for {msg} -- unready: {', '.join(names)}"
            self.fail(error_msg)
        return
