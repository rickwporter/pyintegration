#!/usr/bin/env python3
import os
import sys

from argparse import ArgumentParser
from argparse import Namespace

from pyintegration import IntegrationTestRunner

from constants import TEST_PETSTORE_IMAGE


class PetstoreTestRunner(IntegrationTestRunner):
    def __init__(self):
        super().__init__(description="PetStore integration test runner")

    def addUserArgs(self, parser: ArgumentParser) -> ArgumentParser:
        parser.add_argument(
            "-i", "--image", dest="image_name", type=str, help="PetStore image name"
        )
        return parser

    def processUserArgs(self, args: Namespace) -> None:
        env = os.environ
        if args.image_name:
            env[TEST_PETSTORE_IMAGE] = args.image_name
        return


if __name__ == "__main__":
    runner = PetstoreTestRunner()
    rval = runner.run(sys.argv[1:])
    sys.exit(rval)
