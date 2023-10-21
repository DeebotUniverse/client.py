"""Stats messages."""
from typing import Any

from deebot_client.event_bus import EventBus
from deebot_client.events import CleanJobStatus, ReportStatsEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict


class ReportStats(MessageBodyDataDict):
    """Report stats message."""

    name = "reportStats"

    xml_name = "GetReportStats"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        status = CleanJobStatus.CLEANING
        if "stop" not in data:
            status = CleanJobStatus.NO_STATUS
        elif data["stop"] != 0:
            status = CleanJobStatus(int(data["stopReason"]))

        stats_event = ReportStatsEvent(
            area=data.get("area"),
            time=data.get("time"),
            type=data.get("type"),
            cleaning_id=data["cid"],
            status=status,
            content=[int(float(x)) for x in data.get("content", "").split(",") if x],
        )
        event_bus.notify(stats_event)
        return HandlingResult.success()

    @classmethod
    def _handle_body_data_xml(
        cls, event_bus: EventBus, xml_message: str
    ) -> HandlingResult:
        raise NotImplementedError
