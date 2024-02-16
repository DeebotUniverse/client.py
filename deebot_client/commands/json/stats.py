"""Stats commands."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import TotalStatsEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.messages.json import OnStats

from .common import JsonCommandWithMessageHandling

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetStats(JsonCommandWithMessageHandling, OnStats):
    """Get stats command."""

    name = "getStats"


class GetTotalStats(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get stats command."""

    name = "getTotalStats"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(TotalStatsEvent(data["area"], data["time"], data["count"]))
        return HandlingResult.success()
