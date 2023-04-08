from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# NOTE: these constants are used to determine tag names
ERROR = "error"
FAILURE = "failure"
SKIPPED = "skipped"
SUCCESS = "success"


@dataclass
class TestCaseResults:
    testname: str
    classname: str
    filename: str
    line: int
    result: Optional[str] = None
    message: Optional[str] = None
    starttime: Optional[datetime] = None
    endtime: Optional[datetime] = None


