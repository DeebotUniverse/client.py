"""Custom area mode command module."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import CustomAreaMode, CustomAreaModeEvent
from deebot_client.message import HandlingResult
from deebot_client.util import get_enum

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetCustomAreaMode(JsonGetCommand):
    """Get the cleaning speed command."""

    NAME = "getCustomAreaMode"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(CustomAreaModeEvent(CustomAreaMode(int(data["sweepMode"]))))
        return HandlingResult.success()


class SetCustomAreaMode(JsonSetCommand):
    """Set the cleaning speed command."""

    NAME = "setCustomAreaMode"
    get_command = GetCustomAreaMode
    _mqtt_params = MappingProxyType({"sweepMode": InitParam(CustomAreaMode, "mode")})

    def __init__(self, mode: CustomAreaMode | str) -> None:
        if isinstance(mode, str):
            mode = get_enum(CustomAreaMode, mode)
        super().__init__({"sweepMode": mode.value})
