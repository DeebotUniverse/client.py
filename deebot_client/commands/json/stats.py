"""Stats commands."""
from typing import Any

from deebot_client.events import StatsEvent, TotalStatsEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import EventBus, NoArgsCommand


class GetStats(NoArgsCommand, MessageBodyDataDict):
    """Get stats command."""

    name = "getStats"

    xml_name = "GetStats"

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

    @classmethod
    def _handle_body_data_xml(
        cls, event_bus: EventBus, xml_message: str
    ) -> HandlingResult:
        raise NotImplementedError


class GetTotalStats(NoArgsCommand, MessageBodyDataDict):
    """Get stats command."""

    name = "getTotalStats"

    xml_name = "GetTotalStats"

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

    @classmethod
    def _handle_body_data_xml(
        cls, event_bus: EventBus, xml_message: str
    ) -> HandlingResult:
        raise NotImplementedError
