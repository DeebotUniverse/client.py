"""Stats commands."""
from typing import Any, Dict

from ..events import CleanJobStatus, ReportStatsEvent
from ..events.event_bus import EventBus
from ..message import HandlingResult, Message


class ReportStats(Message):
    """Report stats message."""

    name = "reportStats"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        status = CleanJobStatus.CLEANING

        if data["stop"] != 0:
            status = CleanJobStatus(int(data["stopReason"]))

        stats_event = ReportStatsEvent(
            area=data.get("area"),
            time=data.get("time"),
            type=data.get("type"),
            cleaning_id=data["cid"],
            status=status,
            rooms=[int(x) for x in data.get("content", "").split(",")],
        )
        event_bus.notify(stats_event)
        return HandlingResult.success()
