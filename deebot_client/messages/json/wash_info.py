"""WashInfo messages."""
from typing import Any

from deebot_client.event_bus import EventBus
from deebot_client.events import WashInfoEvent
from deebot_client.events.wash_info import WashMode
from deebot_client.message import HandlingResult, MessageBodyDataDict


class OnWashInfo(MessageBodyDataDict):
    """On battery message."""

    name = "onWashInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(
            WashInfoEvent(
                mode=WashMode(int(data["mode"])),
                hot_wash_amount=data["hot_wash_amount"],
                interval=data["interval"],
            )
        )
        return HandlingResult.success()
