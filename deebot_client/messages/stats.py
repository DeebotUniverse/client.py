"""Stats commands."""
import logging
from typing import Any, Dict

from ..events import CleanJobStatus, ReportStatsEventDto
from ..events.event_bus import EventBus
from ..message import Message

_LOGGER = logging.getLogger(__name__)


class ReportStats(Message):
    """Report stats message."""

    name = "reportStats"

    @classmethod
    def _handle_body_data_dict(cls, event_bus: EventBus, data: Dict[str, Any]) -> bool:
        """Handle message->body->data and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """
        status = CleanJobStatus(int(data.get("stopReason", -1)))

        if data["stop"] == 0:
            status = CleanJobStatus.CLEANING

        stats_event = ReportStatsEventDto(
            area=data.get("area"),
            time=data.get("time"),
            type=data.get("type"),
            clean_id=data["cid"],
            status=status,
            rooms=[int(x) for x in data.get("content", "").split(",")],
        )
        event_bus.notify(stats_event)
        return True
