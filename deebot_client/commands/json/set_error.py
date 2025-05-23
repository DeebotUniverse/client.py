"""SetError commands."""

from __future__ import annotations

from .common import ExecuteCommand

from deebot_client.const import PATH_API_IOT_CONTROL

class SetError(ExecuteCommand):
    """SetError state command."""

    NAME = "setError"

    def __init__(self, code: int) -> None:
        super().__init__({
            "data": {
                "act": "remove",
                "code": [code]
            }
        })
        self._api_path = PATH_API_IOT_CONTROL
