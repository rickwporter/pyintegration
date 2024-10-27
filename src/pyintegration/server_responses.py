from typing import Any
from typing import Dict

from .response_info import ResponseInfo


class ServerResponses:
    """
    Convenience class to manage data
    """

    def __init__(self, base_path: str = ""):
        self.base_path = base_path.strip("/")
        self.responses: Dict[str, Dict[str, ResponseInfo]] = {}

    def fullpath(self, path: str) -> str:
        # if already starts with base_path, no need to prepend that
        if path.startswith(self.base_path):
            return path
        return "/".join(self.base_path, path.strip("/"))

    def add_response(self, path: str, method: str, data: ResponseInfo) -> None:
        fullpath = self.fullpath(path)
        path_data = self.responses.get(fullpath, {})
        path_data[method] = data
        self.responses[fullpath] = path_data

    def for_server(self) -> Dict[str, Any]:
        result = {}
        for path, path_methods in self.responses.items():
            path_data = {
                method: info.as_dict() for method, info in path_methods.items()
            }
            result[path] = path_data

        return result
