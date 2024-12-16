"""Clean count command module."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import CleanCountEvent
from deebot_client.message import HandlingResult

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetCleanCount(JsonGetCommand):
    """Get clean count command."""

    NAME = "getCleanCount"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(CleanCountEvent(count=data["count"]))
        return HandlingResult.success()


class SetCleanCount(JsonSetCommand):
    """Set clean count command."""

    NAME = "setCleanCount"
    get_command = GetCleanCount
    _mqtt_params = MappingProxyType({"count": InitParam(int)})

    def __init__(self, count: int) -> None:
        super().__init__({"count": count})
