import dataclasses
from typing import Any
from typing import Dict
from typing import Union


@dataclasses.dataclass
class ResponseInfo:
    status: int = 200
    headers: Union[None, Dict[str, str]] = None
    body: Union[None, str, Dict[str, Any]] = None
    filename: Union[None, str] = None
    content_type: Union[None, str] = "application/json"
    capture: Union[None, bool] = None

    def as_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)
