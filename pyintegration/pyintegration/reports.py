from typing import Dict
from typing import List

from .testcase_results import ERROR
from .testcase_results import FAILURE
from .testcase_results import SKIPPED
from .testcase_results import SUCCESS
from .testcase_results import TestCaseResults


def count_result(items: List[TestCaseResults], result: str) -> int:
    return len([x for x in items if x.result == result])


def print_props(props: Dict) -> str:
    return " ".join(f"{k}={v}" for k, v in props.items())


def write_reports(results) -> None:
    suites = {}
    for item in results.testCaseData.values():
        name = item.classname
        entries = suites[name] if name in suites else []
        entries.append(item)
        suites[name] = entries

    for classname, testcases in suites.items():
        suite_props = {
            "name": classname,
            "tests": len(testcases),
            "failures": count_result(testcases, FAILURE),
            "errors": count_result(testcases, ERROR),
            "skipped": count_result(testcases, SKIPPED),
            "success": count_result(testcases, SUCCESS),
            "filename": next(iter(testcases)).filename,  # just grab filename from the first item
        }
        print("Suite: " + print_props(suite_props))

        for test in testcases:
            delta = test.endtime - test.starttime
            case_props = {
                "name": test.testname,
                # 'classname': test.classname,
                # 'file': f"{test.filename}:{test.line}",
                "line": test.line,
                "timestamp": test.starttime.isoformat(),
                "time": delta.total_seconds(),
                "status": test.result,
            }
            print("    Case: " + print_props(case_props))


