"""Auto empty messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.auto_empty import Event, Frequency
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnAutoEmpty(MessageBodyDataDict):
    """On auto empty message."""

    name = "onAutoEmpty"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        frequency: Frequency | None = None
        if frequency_str := data.get("frequency"):
            frequency = Frequency(frequency_str)
        event_bus.notify(Event(bool(data["enable"]), frequency))
        return HandlingResult.success()
