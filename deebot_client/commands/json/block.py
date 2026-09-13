"""Quiet-hours block commands."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import BlockEvent
from deebot_client.message import HandlingResult

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetBlock(JsonGetCommand):
    """Get quiet-hours block command."""

    NAME = "getBlock"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(
            BlockEvent(
                enabled=bool(data["enable"]),
                start=str(data["start"]),
                end=str(data["end"]),
            )
        )
        return HandlingResult.success()


class SetBlock(JsonSetCommand):
    """Set quiet-hours block command."""

    NAME = "setBlock"
    get_command = GetBlock
    _mqtt_params = MappingProxyType(
        {
            "enable": InitParam(bool),
            "start": InitParam(str),
            "end": InitParam(str),
        }
    )

    def __init__(self, enable: bool, start: str, end: str) -> None:
        super().__init__({"enable": 1 if enable else 0, "start": start, "end": end})
