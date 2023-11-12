"""Network commands."""
from typing import Any

from deebot_client.event_bus import EventBus
from deebot_client.events import NetworkInfoEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import CommandWithMessageHandling


class GetNetInfo(CommandWithMessageHandling, MessageBodyDataDict):
    """Get network info command."""

    name = "getNetInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """

        event_bus.notify(
            NetworkInfoEvent(
                ip=data["ip"],
                ssid=data["ssid"],
                rssi=int(data["rssi"]),
                mac=data["mac"],
            )
        )
        return HandlingResult.success()
