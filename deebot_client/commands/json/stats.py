"""Stats commands."""
from math import floor
from typing import Any

from deebot_client.event_bus import EventBus
from deebot_client.events import StatsEvent, TotalStatsEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import JsonCommandWithMessageHandling


class GetStats(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get stats command."""

    name = "getStats"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        stats_event = StatsEvent(
            area=data.get("area"),
            time=data.get("time"),
            type=data.get("type"),
        )
        event_bus.notify(stats_event)
        return HandlingResult.success()


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
        stats_event = TotalStatsEvent(
            data["area"],
            floor(data["time"] / 60),  # Convert seconds to minutes
            data["count"],
        )
        event_bus.notify(stats_event)
        return HandlingResult.success()
