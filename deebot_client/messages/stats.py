"""Stats commands."""
import logging
from typing import Any, Dict

from ..events import CleanJobStopReason, ReportStatsEventDto
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
        if data.get("stop", 0) != 1:
            _LOGGER.debug("Stop != 1; Ignoring %s", data)
            return True

        stats_event = ReportStatsEventDto(
            data.get("area"),
            data.get("cid"),
            data.get("time"),
            data.get("type"),
            data.get("start"),
            CleanJobStopReason(int(data.get("stopReason", -1))),
            [int(x) for x in data.get("content", "").split(",")],
        )
        event_bus.notify(stats_event)
        return True
