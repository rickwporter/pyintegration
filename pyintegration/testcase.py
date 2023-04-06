import os
import shlex
import subprocess
import unittest
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional

from .result import Result

# These are environment variable names used by the application
CT_API_KEY = "CLOUDTRUTH_API_KEY"
CT_ENV = "CLOUDTRUTH_ENVIRONMENT"
CT_PROFILE = "CLOUDTRUTH_PROFILE"
CT_PROJ = "CLOUDTRUTH_PROJECT"
CT_URL = "CLOUDTRUTH_SERVER_URL"
CT_TIMEOUT = "CLOUDTRUTH_REQUEST_TIMEOUT"
CT_REST_DEBUG = "CLOUDTRUTH_REST_DEBUG"
CT_REST_SUCCESS = "CLOUDTRUTH_REST_SUCCESS"
CT_REST_PAGE_SIZE = "CLOUDTRUTH_REST_PAGE_SIZE"

DEFAULT_SERVER_URL = "https://api.cloudtruth.io"
DEFAULT_ENV_NAME = "default"
DEFAULT_PROFILE_NAME = "default"

AUTO_DESCRIPTION = "Automated testing via live_test"
TEST_PAGE_SIZE = 5

CT_TEST_LOG_COMMANDS = "CT_LIVE_TEST_LOG_COMMANDS"
CT_TEST_LOG_OUTPUT = "CT_LIVE_TEST_LOG_OUTPUT"
CT_TEST_LOG_COMMANDS_ON_FAILURE = "CT_LIVE_TEST_LOG_COMMANDS_ON_FAILURE"
CT_TEST_LOG_OUTPUT_ON_FAILURE = "CT_LIVE_TEST_LOG_OUTPUT_ON_FAILURE"
CT_TEST_JOB_ID = "CT_LIVE_TEST_JOB_ID"
CT_TEST_KNOWN_ISSUES = "CT_LIVE_TEST_KNOWN_ISSUES"

SRC_ENV = "shell"
SRC_ARG = "argument"
SRC_PROFILE = "profile"
SRC_DEFAULT = "default"

REDACTED = "*****"
DEFAULT_PARAM_VALUE = "-"

# properties
PROP_CREATED = "Created At"
PROP_DESC = "Description"
PROP_MODIFIED = "Modified At"
PROP_NAME = "Name"
PROP_RAW = "Raw"
PROP_TYPE = "Type"
PROP_VALUE = "Value"

REGEX_REST_DEBUG = re.compile("^URL \\w+ .+? elapsed: [\\d\\.]+\\w+$")


def get_cli_base_cmd() -> str:
    """
    This is a separate function that does not reference the `self._base_cmd' so it can be called
    during __init__(). It returns the path to the executable (presumably) with the trailing
    space to allow for easier consumption.
    """
    # walk back up looking for top of projects, and goto `target/debug/cloudtruth`
    curr = Path(__file__).absolute()
    exec_name = "cloudtruth.exe" if os.name == "nt" else "cloudtruth"
    exec_path_release = Path("target") / "release" / exec_name
    exec_path_debug = Path("target") / "debug" / exec_name

    # leverage current structure... walk back up a maximum of 2 levels
    for _ in range(3):
        possible_debug = curr.parent / exec_path_debug
        possible_release = curr.parent / exec_path_release
        # print(possible_debug, possible_release, sep="\n")
        # prefer latest build if both exist
        if possible_debug.exists() and possible_release.exists():
            if os.path.getmtime(possible_debug) > os.path.getmtime(possible_release):
                return str(possible_debug) + " "
            else:
                return str(possible_release) + " "
        if possible_debug.exists():
            return str(possible_debug) + " "
        if possible_release.exists():
            return str(possible_release) + " "
        curr = curr.parent

    # we failed to find this, so just use the "default".
    return exec_name + " "


def find_by_prop(entries: List[Dict], prop_name: str, prop_value: str) -> List[Dict]:
    return [e for e in entries if e.get(prop_name, None) == prop_value]


def missing_any(env_var_names: List[str]) -> bool:
    return not all([os.environ.get(x) for x in env_var_names])


# decorator to mark a test as a known issue
def skip_known_issue(msg: str):
    return unittest.skipUnless(os.environ.get(CT_TEST_KNOWN_ISSUES), f"Known issue: {msg}")


class TestCase(unittest.TestCase):
    """
    This extends the unittest.TestCase to add some basic functions
    """

    def __init__(self, *args, **kwargs):
        self._base_cmd = get_cli_base_cmd()
        self.log_commands = int(os.environ.get(CT_TEST_LOG_COMMANDS, "0"))
        self.log_output = int(os.environ.get(CT_TEST_LOG_OUTPUT, "0"))
        self.log_commands_on_failure = int(os.environ.get(CT_TEST_LOG_COMMANDS_ON_FAILURE, "0"))
        self.log_output_on_failure = int(os.environ.get(CT_TEST_LOG_OUTPUT_ON_FAILURE, "0"))
        self.job_id = os.environ.get(CT_TEST_JOB_ID)
        self._failure_logs = None
        self._filenames = None
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def setUp(self) -> None:
        # collects logs to display when/if the test case fails
        self._failure_logs = list()
        self._filenames = set()
        super().setUp()

    def tearDown(self) -> None:
        # Report test failures
        if not self.log_commands and self.log_commands_on_failure or not self.log_output and self.log_output_on_failure:
            # Python 3.4 - 3.10
            if hasattr(self._outcome, "errors"):
                result = self.defaultTestResult()
                self._feedErrorsToResult(result, self._outcome.errors)
            # Python 3.11+
            else:
                result = self._outcome.result
            success = all(test != self for test, _ in result.errors + result.failures)
            if not success:
                print()  # gives better reading output
                print("\n".join(self._failure_logs))

        # remove any added files
        for fname in self._filenames:
            os.remove(fname)

        super().tearDown()

    def write_file(self, filename: str, content: str) -> None:
        """
        Utility to open set the filename content, and save the name in the list
        for deletion.
        """
        self._filenames.add(filename)
        file = open(filename, "w")
        file.write(content)
        file.close()

    def delete_file(self, filename):
        self._filenames.remove(filename)
        os.remove(filename)

    def make_name(self, name: str) -> str:
        """
        Adds the JOB_ID to the name if present, so multiple tests can run simultaneously.
        """
        if not self.job_id:
            return name
        return name + "-" + self.job_id

    def get_cmd_env(self):
        env_copy = deepcopy(os.environ)
        ## temporarily unset the CLOUDTRUTH_REST_DEBUG environment variable if defined, so that
        ## in run_cli_cmd() we can detect if a test explicitly set it. this allows us to determine if
        ## we should keep the debug logs in stdout for tests that explicitly assert on them (ex: test_timing.py),
        ## or if we should strip debug logs from stdout to prevent assertion failures in tests that are not
        ## expecting debug logs.
        if env_copy.get(CT_REST_DEBUG, "false").lower() in ("true", "1", "y", "yes"):
            del env_copy[CT_REST_DEBUG]
        return env_copy

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

    def assertPaginated(self, cmd_env, command: str, in_req: str, page_size: int = TEST_PAGE_SIZE):
        """
        Sets an artificially low CLOUDTRUTH_REST_PAGE_SIZE so we get paginated results for the
        provided command, and checks the output includes the URLs that specify additional pages.
        """
        local_env = deepcopy(cmd_env)
        local_env[CT_REST_DEBUG] = "true"
        local_env[CT_REST_PAGE_SIZE] = str(page_size)
        result = self.run_cli(local_env, command)
        self.assertResultSuccess(result)
        gets = [_ for _ in result.stdout if "URL GET" in _ and in_req in _]
        size_search = f"page_size={page_size}"
        size_spec = [_ for _ in gets if size_search in _]
        self.assertGreaterEqual(len(size_spec), 2)  # should have at least 2 paginated requests
        self.assertGreaterEqual(len([_ for _ in gets if "page=1" in _]), 1)
        self.assertGreaterEqual(len([_ for _ in gets if "page=2" in _]), 1)

    def run_cli(self, env: Dict[str, str], cmd: str) -> Result:  # noqa: C901
        # WARNING: DOS prompt does not like the single quotes, so use double
        cmd = cmd.replace("'", '"')

        if self.log_commands:
            print(cmd)
        elif self.log_commands_on_failure:
            self._failure_logs.append(cmd)

        def _next_part(arg_list: List, key: str) -> str:
            """Simple function to walk the 'arg_list' and find the item after the 'key'"""
            for index, value in enumerate(arg_list):
                if value == key:
                    return arg_list[index + 1]
            return None

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
        elif self.log_output_on_failure:
            if result.stdout:
                self._failure_logs.append("\n".join(result.stdout))
            if result.stderr:
                self._failure_logs.append("\n".join(result.stderr))
        elif self.rest_debug:
            debug_out = [line for line in result.stdout if re.match(REGEX_REST_DEBUG, line)]
            if debug_out:
                print("\n".join(debug_out))
