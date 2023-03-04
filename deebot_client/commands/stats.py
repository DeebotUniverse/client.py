"""Stats commands."""
from typing import Any

from ..events import StatsEvent, TotalStatsEvent
from ..message import HandlingResult, MessageBodyDataDict
from .common import EventBus, NoArgsCommand


class GetStats(NoArgsCommand, MessageBodyDataDict):
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


class GetTotalStats(NoArgsCommand, MessageBodyDataDict):
    """Get stats command."""

    name = "getTotalStats"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        stats_event = TotalStatsEvent(data["area"], data["time"], data["count"])
        event_bus.notify(stats_event)
        return HandlingResult.success()
