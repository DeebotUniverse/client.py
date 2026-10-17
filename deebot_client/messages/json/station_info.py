"""Base station info messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.station import StationInfoEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnStationInfo(MessageBodyDataDict):
    """On station info message."""

    NAME = "onStationInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(
            StationInfoEvent(
                name=data["name"],
                model=data["model"],
                firmware=data["wkVer"],
            )
        )
        return HandlingResult.success()
