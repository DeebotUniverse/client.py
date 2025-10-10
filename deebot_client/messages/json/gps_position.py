"""GPS position messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import GpsPositionEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnGpsPos(MessageBodyDataDict):
    """On GPS position message."""

    NAME = "onGpsPos"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(
            GpsPositionEvent(
                longitude=float(data["longitude"]), latitude=float(data["latitude"])
            )
        )
        return HandlingResult.success()
