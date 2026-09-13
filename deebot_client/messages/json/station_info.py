"""Base station info messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.station import StationInfoEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


def _as_str(value: Any) -> str:
    """Return the value when it is a string, else an empty string."""
    return value if isinstance(value, str) else ""


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
                name=_as_str(data.get("name")),
                model=_as_str(data.get("model")),
                firmware=_as_str(data.get("wkVer")),
            )
        )
        return HandlingResult.success()
