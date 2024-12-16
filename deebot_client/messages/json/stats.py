"""Stats messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import CleanJobStatus, ReportStatsEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class ReportStats(MessageBodyDataDict):
    """Report stats message."""

    NAME = "reportStats"

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
