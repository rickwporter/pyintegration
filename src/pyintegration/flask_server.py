import logging
import json
from threading import Thread
from time import sleep
from typing import Any
from typing import Dict
from typing import Optional

from flask import Flask
from flask import Response
from flask import request
from werkzeug.serving import make_server


class FlaskApp(Flask):
    def __init__(self):
        super().__init__(__name__)
        self.response_data: Dict[str, Any] = {}
        self.request_data: Dict[str, Any] = {}
        self.statistics: Dict[str, int] = {}
        # add a single rule to make sure to handle all requests
        self.add_url_rule(
            "/<path:path>",
            view_func=self.process_request,
            methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"],
        )

    @staticmethod
    def _find_data(data: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
        """Provides convenient way to find the data (ignores case and leading/trailing slashes)"""

        def _annon(s: str) -> str:
            return s.lower().strip("/")

        needle = _annon(name)
        for key, value in data.items():
            mod_path = _annon(key)
            if needle == mod_path:
                return value

        return None

    def set_response_data(self, data: Dict[str, Any]) -> None:
        self.response_data = data

    def get_request_data(self, path: str) -> Optional[Dict[str, Any]]:
        return self._find_data(self.request_data, path)

    def get_statistics(self) -> Dict[str, int]:
        return self.statistics

    def reset_statistics(self) -> None:
        self.statistics = {}

    def process_request(self, path: str) -> Response:
        method = request.method

        # update statistics
        stats_key = f"{method} {path}"
        self.statistics[stats_key] = self.statistics.get(stats_key, 0) + 1

        path_data = self._find_data(self.response_data, path)
        if path_data is None:
            return Response(
                status=404, response=json.dumps({"error": f"No path for {path}"})
            )
        method_data = self._find_data(path_data, method)
        if method_data is None:
            return Response(
                status=404,
                response=json.dumps({"error": f"No {method} method for path {path}"}),
            )

        if method_data.get("capture", False):
            self.request_data[path] = json.loads(request.data)

        response = Response(
            status=method_data.get("status", 200),
            response=json.dumps(method_data.get("body", None)),
            content_type=method_data.get("content_type", "application/json"),
            headers=method_data.get("headers", None),
        )
        filename = method_data.get("filename")
        if filename:
            response.set_data(open(filename, "rb").read())

        return response


class FlaskThread(Thread):
    def __init__(self, app: FlaskApp, host: str, port: int):
        super().__init__()
        self.app = app
        self.server = make_server(host, port, app)

    def run(self):
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass

    def shutdown(self):
        self.server.shutdown()

    def ready(self) -> bool:
        return self.server.port != 0

    def get_base_url(self) -> str:
        return f"http://{self.server.host}:{self.server.port}"

    def set_response_data(self, data: Dict[str, Any]) -> None:
        self.app.set_response_data(data)

    def get_request_data(self, path: str) -> Optional[Dict[str, Any]]:
        return self.app.get_request_data(path)

    def get_statistics(self) -> Dict[str, int]:
        return self.app.get_statistics()

    def reset_statistics(self) -> None:
        self.app.reset_statistics()


def set_server_log_level(log_level: str) -> None:
    logging.getLogger("werkueg").setLevel(log_level)


def start_server(
    host: str = "127.0.0.1", port: int = 0, log_level: str = "WARNING"
) -> FlaskThread:
    set_server_log_level(log_level)
    app = FlaskApp()
    thread = FlaskThread(app, host, port)
    thread.start()
    while not thread.ready():
        sleep(1)

    return thread
