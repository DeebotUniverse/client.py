"""WashInfo messages."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import WashInfoEvent
from deebot_client.events.wash_info import WashMode
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


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
        mode = data.get("mode")
        if isinstance(mode, int):
            mode = WashMode(mode)

        event_bus.notify(
            WashInfoEvent(
                mode=mode,
                hot_wash_amount=data.get("hot_wash_amount"),
                interval=data.get("interval"),
            )
        )
        return HandlingResult.success()
