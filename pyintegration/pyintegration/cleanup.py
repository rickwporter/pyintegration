import argparse
import docker
import os
import re

from pathlib import Path
from typing import List
from typing import Optional


DEFAULT_DESCRIPTION = "Cleanup stray integration test containers"
CLASS_RE = re.compile(r"class\s+(?P<clazzname>\S+)\(\S+TestCase\)")


class Cleanup:
    """
    Basis for a command to delete stray containers
    """
    def __init__(self, description: str = DEFAULT_DESCRIPTION, path: Optional[str] = None):
        self.description = description
        self.path = path if path else os.getcwd()

    def parse_args(self, *args) -> argparse.Namespace:
        parser = argparse.ArgumentParser(description=self.description)
        parser.add_argument(
            "-f",
            "--force",
            dest="force",
            action="store_true",
            help="Force removate without prompting",
        )
        parser.add_argument(
            "--filter",
            dest="filter_prefixes",
            nargs="+",
            default=self.getTestClasses(),
            help="Only include containers with these in the name (default: %(default)s)"
        )
        parser.add_argument(
            "-j",
            "--job-id",
            dest="job_id",
            type=str,
            help="Job Identifier to use as a suffix on project name"
        )
        parser.add_argument(
            "-p",
            "--path",
            dest="path",
            default=self.path,
            help="Path to tests (default: %(default)s)"
        )
        return parser.parse_args(*args)

    def getTestClasses(self) -> List[str]:
        """
        Returns a list of classes dervived from a TestCase.
        """
        suitenames = []
        dir = Path(self.path)
        files = [_ for _ in dir.iterdir() if _.is_file() and _.name.endswith('.py') and _.name.startswith('test_')]
        for f in files:
            for match in CLASS_RE.finditer(f.read_text()):
                suitenames.append(match.group("clazzname"))
        return suitenames

    def yes_or_no(self, question: str) -> bool:
        reply = str(input(question + " (y/n): ")).lower().strip()
        if reply[0] == "y":
            return True
        if reply[0] == "n":
            return False
        return self.yes_or_no("Please enter ")

    def run(self, *args) -> int:
        args = self.parse_args(*args)
        prefixes = args.filter_prefixes
        job_id = args.job_id
        force = args.force

        dockerClient = docker.from_env()
        containers = [_ for _ in dockerClient.containers.list() if any([_.name.startswith(p) for p in prefixes])]
        if job_id:
            containers = [_ for _ in containers if _.name.endswith(job_id)]

        if not containers:
            print("No containers matching filter/job-id")
            return 0

        NL = '\n    '
        print("Container to be removed:" + NL + NL.join([f"{_.name} ({_.short_id})" for _ in containers]))

        if not force:
            remove = self.yes_or_no("Remove teh above containers")
            if not remove:
                print("No containers removed")
                return 0

        for c in containers:
            c.stop()
        return 0
