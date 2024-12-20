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
DELETE = "DELETE"
PATCH = "PATCH"
PUT = "PUT"
TRACE = "TRACE"

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
        self.responses = ServerResponses()

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

    def add_response(self, url: str, method: str, data: ResponseInfo) -> None:
        self.responses.add_response(url, method, data)

    def set_server_responses(self) -> None:
        self.set_response_data(self.responses.for_server())

    def set_server_logging(self, level: str):
        self.set_server_logging(level)

    def set_response_data(self, data: Optional[Dict[str, Any]]):
        self.server.set_response_data(data)

    def test_mock_no_data(self):
        base_url = self.address
        resp = self.request(base_url + "/some_url")
        self.assertEqual(404, resp.status_code)

    def test_mock_simple_json(self):
        self.add_response(
            SIMPLE_URL, GET, ResponseInfo(body={"foo": "bar"}, content_type=None)
        )
        self.set_server_responses()
        base_url = self.address
        resp = self.request(f"{base_url}/{SIMPLE_URL}")
        self.assertEqual(200, resp.status_code)
        self.assertEqual({"foo": "bar"}, resp.json())
        # without specifying a type, this gets assigned by Flask
        self.assertEqual(resp.headers.get(CONTENT_TYPE), "text/html; charset=utf-8")

    def test_mock_simple_text(self):
        self.add_response(
            SIMPLE_URL,
            GET,
            ResponseInfo(body="random string", content_type="text/plain"),
        )
        self.set_server_responses()
        base_url = self.address
        resp = self.request(f"{base_url}/{SIMPLE_URL}")
        self.assertEqual(200, resp.status_code)
        self.assertEqual('"random string"', resp.text)
        self.assertEqual(resp.headers.get(CONTENT_TYPE), "text/plain")

    def test_mock_headers(self):
        self.add_response(
            SIMPLE_URL, GET, ResponseInfo(headers={"sna": "foo", "foo": "bar"})
        )
        self.set_server_responses()
        base_url = self.address
        resp = self.request(f"{base_url}/{SIMPLE_URL}")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(resp.headers.get("Content-Type"), "application/json")
        self.assertEqual(resp.headers.get("sna"), "foo")
        self.assertEqual(resp.headers.get("foo"), "bar")

    def test_mock_status(self):
        base_url = self.address
        url = f"{base_url}/{SIMPLE_URL}"
        for status_code in (200, 202, 204, 303, 401, 503):
            self.add_response(SIMPLE_URL, GET, ResponseInfo(status=status_code))
            self.set_server_responses()
            resp = self.request(url)
            self.assertEqual(status_code, resp.status_code)

    def test_mock_method_and_stats(self):
        base_url = self.address
        url = f"{base_url}/{SIMPLE_URL}"
        METHODS = (GET, POST, DELETE, PUT, PATCH, TRACE)
        for method in METHODS:
            self.add_response(SIMPLE_URL, method, ResponseInfo())
            self.set_server_responses()
            stat_key = f"{method} {SIMPLE_URL}"
            self.assertIsNone(self.server.get_statistics().get(stat_key))
            resp = self.request(url, method=method)
            self.assertEqual(200, resp.status_code)
            self.assertEqual(1, self.server.get_statistics().get(stat_key))

        expected_stats = {f"{m} {SIMPLE_URL}": 1 for m in METHODS}
        self.assertEqual(expected_stats, self.server.get_statistics())

    def test_mock_file(self):
        base_url = self.address
        file = Path(__file__).parent.parent / "README.md"
        self.add_response(
            SIMPLE_URL, GET, ResponseInfo(filename=str(file), content_type="text/plain")
        )
        self.set_server_responses()
        resp = self.request(f"{base_url}/{SIMPLE_URL}")
        self.assertEqual(200, resp.status_code)
        self.assertEqual("text/plain", resp.headers.get(CONTENT_TYPE))
        self.assertEqual(file.read_bytes(), resp.content)

    def test_mock_capture(self):
        base_url = self.address
        body = {"abc": 123, "def": "ghi", "jkl": True}
        message = "simple error message"
        self.add_response(
            SIMPLE_URL, POST, ResponseInfo(body=message, status=403, capture=True)
        )
        self.set_server_responses()
        resp = self.request(f"{base_url}/{SIMPLE_URL}", POST, data=body)
        self.assertEqual(403, resp.status_code)
        self.assertIn(message, resp.text)
        self.assertEqual(body, self.server.get_request_data(SIMPLE_URL))
