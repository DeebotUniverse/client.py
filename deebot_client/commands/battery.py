"""Battery commands."""
import logging
from typing import Any, Dict

from ..events import BatteryEventDto
from ..message import MessageResponse
from .common import EventBus, _NoArgsCommand

_LOGGER = logging.getLogger(__name__)


class GetBattery(_NoArgsCommand):
    """Get battery command."""

    name = "getBattery"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> MessageResponse:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(BatteryEventDto(data["value"]))
        return MessageResponse.success()
