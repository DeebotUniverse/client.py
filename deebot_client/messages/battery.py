"""Battery messages."""
from typing import Any

from ..events import BatteryEvent
from ..events.event_bus import EventBus
from ..message import HandlingResult, MessageBodyDataDict


class OnBattery(MessageBodyDataDict):
    """On battery message."""

    name = "onBattery"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(BatteryEvent(data["value"]))
        return HandlingResult.success()
