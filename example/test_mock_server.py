import json
import logging
import os
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional

from pyintegration import IntegrationTestCase
from pyintegration import ResponseInfo
from pyintegration import ServerResponses
from pyintegration import set_server_log_level
from pyintegration import start_server

GET = "GET"
POST = "POST"

CONTENT_TYPE = "Content-Type"

SIMPLE_URL = "sna/foo"

BODY = "body"
HEADERS = "headers"
STATUS = ""

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class TestMockServer(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        set_server_log_level("WARNING")
        self.server = start_server()
        self.address = self.server.get_base_url()

    def tearDown(self):
        self.record_server_stats()
        self.server.shutdown()
        super().tearDown()

    def record_server_stats(self):
        dirname = os.environ.get("STATS_DIR")
        if not dirname:
            return

        stats = self.server.get_statistics()
        dirpath = Path(dirname)
        dirpath.mkdir(parents=True, exist_ok=True)
        with open(f"{dirpath}/{self._testMethodName}.json", "w") as fp:
            json.dump(
                stats, fp, indent=2
            )  # use indent so get one per line for easier comparison

    def set_server_logging(self, level: str):
        self.set_server_logging(level)

    def set_response_data(self, data: Optional[Dict[str, Any]]):
        self.server.set_response_data(data)

    def test_mock_no_data(self):
        base_url = self.address
        resp = self.request(base_url + "/some_url")
        self.assertEqual(404, resp.status_code)

    def test_mock_simple_json(self):
        responses = ServerResponses()
        responses.add_response(
            SIMPLE_URL, GET, ResponseInfo(body={"foo": "bar"}, content_type=None)
        )
        self.set_response_data(responses.for_server())
        base_url = self.address
        resp = self.request(f"{base_url}/{SIMPLE_URL}")
        self.assertEqual(200, resp.status_code)
        self.assertEqual({"foo": "bar"}, resp.json())
        # without specifying a type, this gets assigned by Flask
        self.assertEqual(resp.headers.get(CONTENT_TYPE), "text/html; charset=utf-8")

    def test_mock_simple_text(self):
        responses = ServerResponses()
        responses.add_response(
            SIMPLE_URL,
            GET,
            ResponseInfo(body="random string", content_type="text/plain"),
        )
        self.set_response_data(responses.for_server())
        base_url = self.address
        resp = self.request(f"{base_url}/{SIMPLE_URL}")
        self.assertEqual(200, resp.status_code)
        self.assertEqual('"random string"', resp.text)
        self.assertEqual(resp.headers.get(CONTENT_TYPE), "text/plain")
