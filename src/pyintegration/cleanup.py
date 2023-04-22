import argparse
import os

from typing import Optional


DEFAULT_DESCRIPTION = "Cleanup stray integration test containers"


class Cleanup:
    """
    Basis for a command to delete stray containers
    """
    def __init__(self, description: str = DEFAULT_DESCRIPTION, path: Optional[str] = None):
        self.description = description
        self.path = path if path else os.getcwd()

    def parse_args(self, *args) -> argparse.Namespace:
        parser = argparse.ArgumentParser(description="Cleanup the CloudTruth environment")
        parser.add_argument(
            dest="needles",
            nargs="*",
            default=["Windows", "Linux", "macOS", "ci-cli", "testcli"],
            help="Search strings to look for",
        )
        parser.add_argument(
            "-q",
            "--quiet",
            dest="quiet",
            action="store_true",
            help="Do not show what the script is doing",
        )
        parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="Detailed output")
        parser.add_argument("--confirm", "--yes", dest="confirm", action="store_true", help="Skip confirmation prompt")
        return parser.parse_args(*args)

    def yes_or_no(self, question: str) -> bool:
        reply = str(input(question + " (y/n): ")).lower().strip()
        if reply[0] == "y":
            return True
        if reply[0] == "n":
            return False
        return self.yes_or_no("Please enter ")
