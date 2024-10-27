#!/usr/bin/env python3
import inspect
import os
import pdb
import sys
import traceback
import unittest

from argparse import ArgumentParser
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import List
from typing import Tuple

from .constants import PYINT_CAPTURE
from .constants import PYINT_JOB_ID
from .constants import PYINT_KNOWN_ISSUES
from .constants import PYINT_PRINT_COMMANDS
from .constants import PYINT_PRINT_OUTPUT
from .reports import write_reports
from .testcase_results import ERROR
from .testcase_results import FAILURE
from .testcase_results import SKIPPED
from .testcase_results import SUCCESS
from .testcase_results import TestCaseResults


DEFAULT_DESCRIPTION = "Run integration tests"


def error_message(tb: traceback, ae: AssertionError) -> str:
    return "".join(traceback.format_tb(tb)) + "\n\nAssertion:\n" + str(ae)


def name_from_test(test: unittest.case.TestCase) -> str:
    return test._testMethodName


def debugTestRunner(enable_debug: bool, verbosity: int, failfast: bool):
    """Overload the TextTestRunner to conditionally drop into pdb on an error/failure."""

    class DebugTestResult(unittest.TextTestResult):
        def __init__(self, stream, descriptions, verbosity):
            super().__init__(
                stream=stream, descriptions=descriptions, verbosity=verbosity
            )
            self.testCaseData = {}

        def addError(self, test: unittest.case.TestCase, err) -> None:
            # called before tearDown()
            traceback.print_exception(*err)
            if enable_debug:
                pdb.post_mortem(err[2])
            name = name_from_test(test)
            self.testCaseData[name].result = ERROR
            self.testCaseData[name].message = error_message(err[2], err[1])
            super().addError(test, err)

        def addFailure(self, test: unittest.case.TestCase, err) -> None:
            traceback.print_exception(*err)
            if enable_debug:
                pdb.post_mortem(err[2])
            name = name_from_test(test)
            self.testCaseData[name].result = FAILURE
            self.testCaseData[name].message = error_message(err[2], err[1])
            super().addFailure(test, err)

        def addSuccess(self, test: unittest.case.TestCase) -> None:
            name = name_from_test(test)
            self.testCaseData[name].result = SUCCESS
            super().addSuccess(test)

        def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:
            name = name_from_test(test)
            self.testCaseData[name].result = SKIPPED
            self.testCaseData[name].message = reason
            super().addSkip(test, reason)

        def startTest(self, test: unittest.case.TestCase) -> None:
            super().startTest(test)
            topdir = Path(__file__).parent.absolute().as_posix() + "/"
            name = name_from_test(test)
            fullpath = inspect.getsourcefile(type(test))
            _, line = inspect.getsourcelines(getattr(test, name))
            filename = fullpath.replace(topdir, "")
            classname = test.__module__ + "." + test.__class__.__name__
            data = TestCaseResults(
                name, classname, filename, line, starttime=datetime.now()
            )
            self.testCaseData[name] = data

        def stopTest(self, test: unittest.case.TestCase) -> None:
            super().stopTest(test)
            name = name_from_test(test)
            self.testCaseData[name].endtime = datetime.now()

    return unittest.TextTestRunner(
        verbosity=verbosity,
        failfast=failfast,
        resultclass=DebugTestResult,
        stream=sys.stdout,
    )


def filter_suite(suite, func):
    for testmodule in suite:
        for testsuite in testmodule:
            tests_to_remove = []
            for index, testcase in enumerate(testsuite._tests):
                if func(testcase):
                    tests_to_remove.append(index)

            # do this in reverse order, so index does not change
            for index in reversed(tests_to_remove):
                testsuite._tests.pop(index)
    return suite


def filter_before(suite, before: str):
    def is_before(testcase: str) -> bool:
        return testcase._testMethodName > before

    return filter_suite(suite, is_before)


def filter_after(suite, after: str):
    def is_after(testcase: str) -> bool:
        return testcase._testMethodName < after

    return filter_suite(suite, is_after)


def filter_exclude(suite, exclude: str):
    def is_excluded(testcase: str) -> bool:
        return exclude in testcase._testMethodName

    return filter_suite(suite, is_excluded)


class IntegrationTestRunner:
    def __init__(self, description: str = DEFAULT_DESCRIPTION):
        self.description = description

    def parseArgs(self, *args) -> Namespace:
        """
        Creates the parser, and digests the args into a Namespace
        """
        parser = ArgumentParser(description=self.description)
        parser = self.addDebugArgs(parser)
        parser = self.addOutputArgs(parser)
        parser = self.addFilterArgs(parser)
        parser = self.addControlArgs(parser)
        parser = self.addUserArgs(parser)
        return parser.parse_args(*args)

    def addUserArgs(self, parser: ArgumentParser) -> ArgumentParser:
        """
        This method is intended to be overridden, so is a no-op in the base class
        """
        return parser

    def addDebugArgs(self, parser: ArgumentParser) -> ArgumentParser:
        parser.add_argument(
            "--pdb",
            dest="pdb",
            action="store_true",
            help="Open the debugger when a test fails",
        )
        parser.add_argument(
            "--debug",
            dest="debug",
            action="store_true",
            help="Equivalent of --pdb --failfast",
        )
        parser.add_argument(
            "--failfast",
            action="store_true",
            help="Stop the test on first error",
        )
        return parser

    def addOutputArgs(self, parser: ArgumentParser) -> ArgumentParser:
        parser.add_argument(
            "-v",
            "--verbosity",
            type=int,
            default=3,
            metavar="LEVEL",
            help="Unittest verbosity level (default: %(default)s)",
        )
        parser.add_argument(
            "-pc",
            "--print-commands",
            dest="print_commands",
            action="store_true",
            help="Print the commands to stdout",
        )
        parser.add_argument(
            "-po",
            "--print-output",
            dest="print_output",
            action="store_true",
            help="Print the output to stdout",
        )
        parser.add_argument(
            "-pa",
            "--print-all",
            dest="print_all",
            action="store_true",
            help="Print the output and commands to stdout",
        )
        parser.add_argument(
            "-c",
            "--capture",
            dest="capture_scheme",
            metavar="OPTION",
            choices=["all", "success", "failure"],
            default="failure",
            help="When to capture output (default: %(default)s)",
        )
        parser.add_argument(
            "-r", "--reports", dest="reports", action="store_true", help="Write reports"
        )
        return parser

    def addFilterArgs(self, parser: ArgumentParser) -> ArgumentParser:
        parser.add_argument(
            "--file",
            dest="file_filter",
            type=str,
            default="test_*.py",
            help="Filter the files run using the specified pattern",
        )
        parser.add_argument(
            "-f",
            "--filter",
            dest="test_filter",
            nargs="+",
            default=[],
            help="Only include tests containing the provided string(s) in the name",
        )
        parser.add_argument(
            "--before",
            dest="before",
            help="Only run tests before the specified string",
        )
        parser.add_argument(
            "--after",
            dest="after",
            help="Only run tests after the specified string",
        )
        parser.add_argument(
            "--exclude",
            dest="test_exclude",
            nargs="+",
            default=[],
            help="Exclude tests containing the provided string(s) in the name",
        )
        parser.add_argument(
            "--known-issues",
            dest="known_issues",
            action="store_true",
            help="don't skip known issues",
        )
        return parser

    def addControlArgs(self, parser: ArgumentParser) -> ArgumentParser:
        parser.add_argument(
            "-l",
            "--list",
            dest="list_only",
            action="store_true",
            help="Only print the tests that will be run (without running them).",
        )
        parser.add_argument(
            "--job-id",
            type=str,
            dest="job_id",
            help="Job Identifier to use as a suffix on project and environment names (default: testcli)",
        )
        return parser

    def setupEnvironment(self, args: Namespace) -> None:
        env = os.environ
        if args.print_all:
            args.print_commands = True
            args.print_output = True
        env[PYINT_PRINT_COMMANDS] = str(int(args.print_commands))
        env[PYINT_PRINT_OUTPUT] = str(int(args.print_output))
        env[PYINT_CAPTURE] = args.capture_scheme
        if args.job_id:
            env[PYINT_JOB_ID] = args.job_id
        if args.known_issues:
            env[PYINT_KNOWN_ISSUES] = args.known_issues

    def findTests(self, args: Namespace) -> Tuple[Any, List[str]]:
        test_directory = "."
        loader = unittest.TestLoader()

        applied_filter = []
        if args.file_filter:
            applied_filter.append(f"file: {args.file_filter}")

        if args.test_filter:
            applied_filter.append(f"filters: {', '.join(args.test_filter)}")
            loader.testNamePatterns = [f"*{_}*" for _ in args.test_filter]
        suite = loader.discover(test_directory, pattern=args.file_filter)

        if args.before:
            applied_filter.append(f"before: {args.before}")
            suite = filter_before(suite, args.before)

        if args.after:
            applied_filter.append(f"after: {args.after}")
            suite = filter_after(suite, args.after)

        if args.test_exclude:
            applied_filter.append(f"excludes: {', '.join(args.test_exclude)}")
            for ex in args.test_exclude:
                suite = filter_exclude(suite, ex)

        return (suite, applied_filter)

    def printSuite(self, suite) -> None:
        if hasattr(suite, "__iter__"):
            for x in suite:
                self.printSuite(x)
        elif hasattr(suite, "_testMethodName"):
            name = getattr(suite, "_testMethodName")
            print(f"{name}")
        else:
            print("invalid")
        return

    def writeReport(self, results) -> None:
        write_reports(results)

    def run(self, *args) -> int:
        args = self.parseArgs(*args)

        # NOTE: setup environment BEFORE instantiating testcases
        self.setupEnvironment(args)
        self.processUserArgs(args)

        (suite, filters) = self.findTests(args)
        if suite.countTestCases() == 0:
            # must be because of a filter or file filter
            sep = "\n\t"
            print(f"No tests matching:{sep}{sep.join(filters)}")
            return 3

        if args.list_only:
            self.printSuite(suite)
            return 0

        debug = args.debug or args.pdb
        failfast = args.debug or args.failfast
        runner = debugTestRunner(
            enable_debug=debug, verbosity=args.verbosity, failfast=failfast
        )
        test_result = runner.run(suite)

        if args.reports:
            self.writeReports(test_result)

        rval = 0
        if len(test_result.errors):
            rval += 1
        if len(test_result.failures):
            rval += 2
        return rval
