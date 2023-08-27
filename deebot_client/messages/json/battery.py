"""Battery messages."""
from typing import Any

from deebot_client.events import BatteryEvent
from deebot_client.events.event_bus import EventBus
from deebot_client.message import HandlingResult, MessageBodyDataDict


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
