"""SetError commands."""

from __future__ import annotations

from .common import ExecuteCommand

from deebot_client.const import PATH_API_IOT_CONTROL
from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.models import ApiDeviceInfo
    from deebot_client.command import CommandResult
    from deebot_client.event_bus import EventBus

class SetError(ExecuteCommand):
    """SetError state command."""

    NAME = "setError"

    def __init__(self, code: int) -> None:
        super().__init__({
            "act": "remove",
            "code": [code]
        })
        self._api_path = PATH_API_IOT_CONTROL

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[CommandResult, dict[str, Any]]:
        return await super()._execute(authenticator, device_info, event_bus)
