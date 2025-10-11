"""Work mode commands."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import WorkMode, WorkModeEvent
from deebot_client.message import HandlingResult
from deebot_client.util import get_enum

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetWorkMode(JsonGetCommand):
    """Get work mode command."""

    NAME = "getWorkMode"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(WorkModeEvent(WorkMode(int(data["mode"]))))
        return HandlingResult.success()


class SetWorkMode(JsonSetCommand):
    """Set work mode command."""

    NAME = "setWorkMode"
    get_command = GetWorkMode
    _mqtt_params = MappingProxyType({"mode": InitParam(WorkMode)})

    def __init__(self, mode: WorkMode | str) -> None:
        if isinstance(mode, str):
            mode = get_enum(WorkMode, mode)
        super().__init__({"mode": mode.value})
