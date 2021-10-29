"""Stats commands."""
import logging
from typing import Any, Dict

from ..events import StatsEventDto, TotalStatsEventDto
from .common import EventBus, _NoArgsCommand

_LOGGER = logging.getLogger(__name__)


class GetStats(_NoArgsCommand):
    """Get stats command."""

    name = "getStats"

    @classmethod
    def _handle_body_data_dict(cls, event_bus: EventBus, data: Dict[str, Any]) -> bool:
        """Handle message->body->data and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """
        stats_event = StatsEventDto(
            data.get("area"),
            data.get("cid"),
            data.get("time"),
            data.get("type"),
            data.get("start"),
        )
        event_bus.notify(stats_event)
        return True


class GetTotalStats(_NoArgsCommand):
    """Get stats command."""

    name = "getTotalStats"

    @classmethod
    def _handle_body_data_dict(cls, event_bus: EventBus, data: Dict[str, Any]) -> bool:
        """Handle message->body->data and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """
        stats_event = TotalStatsEventDto(data["area"], data["time"], data["count"])
        event_bus.notify(stats_event)
        return True
