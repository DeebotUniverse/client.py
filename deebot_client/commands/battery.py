"""Battery commands."""
from typing import Any, Dict

from ..events import BatteryEvent
from ..message import HandlingResult
from .common import EventBus, _NoArgsCommand


class GetBattery(_NoArgsCommand):
    """Get battery command."""

    name = "getBattery"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(BatteryEvent(data["value"]))
        return HandlingResult.success()
