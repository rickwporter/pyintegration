import os
import re
import subprocess
import unittest

from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

from .constants import PYINT_CAPTURE
from .constants import PYINT_JOB_ID
from .constants import PYINT_KNOWN_ISSUES
from .constants import PYINT_LOG_COMMANDS
from .constants import PYINT_LOG_OUTPUT
from .result import Result

REGEX_REST_DEBUG = re.compile("^URL \\w+ .+? elapsed: [\\d\\.]+\\w+$")


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
        self.log_commands : int = int(os.environ.get(PYINT_LOG_COMMANDS, "0"))
        self.log_output : int = int(os.environ.get(PYINT_LOG_OUTPUT, "0"))
        self.capture_scheme: Optional[str] = os.environ.get(PYINT_CAPTURE)
        self.job_id : Optional[int] = os.environ.get(PYINT_JOB_ID)
        self._capture_data : List[str] = None
        self.capture_separator: str = "**************************"
        self._filenames = None
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def setUp(self) -> None:
        # collects logs to display when/if the test case fails
        self._capture_data = list()
        self._filenames = set()
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

    def fullName(self, name: str) -> str:
        """
        Adds the JOB_ID to the name if present, so multiple tests can run simultaneously.
        """
        if not self.job_id:
            return name
        return name + "-" + self.job_id

    def get_display_env_command(self) -> str:
        if os.name == "nt":
            return "SET"
        return "printenv"

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

        if self.log_commands:
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

        ## Log outputs
        if self.log_output:
            if result.stdout:
                print("\n".join(result.stdout))
            if result.stderr:
                print("\n".join(result.stderr))

        self.logResult(result)
        return result
