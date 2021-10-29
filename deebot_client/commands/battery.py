"""Battery commands."""
import logging
from typing import Any, Dict

from ..events import BatteryEventDto
from .common import EventBus, _NoArgsCommand

_LOGGER = logging.getLogger(__name__)


class GetBattery(_NoArgsCommand):
    """Get battery command."""

    name = "getBattery"

    @classmethod
    def _handle_body_data_dict(cls, event_bus: EventBus, data: Dict[str, Any]) -> bool:
        """Handle message->body->data and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """
        try:
            event_bus.notify(BatteryEventDto(data["value"]))
        except ValueError:
            _LOGGER.warning("Couldn't parse battery status: %s", data)
        return True
