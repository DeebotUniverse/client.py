"""Protect state messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.mower import ProtectStateEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnProtectState(MessageBodyDataDict):
    """On protect state message."""

    NAME = "onProtectState"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(
            ProtectStateEvent(
                animal_protection=bool(data["isAnimProtect"]),
                rain_protection=bool(data["isRainProtect"]),
                rain_delay=bool(data["isRainDelay"]),
                emergency_stop=bool(data["isEStop"]),
                locked=bool(data["isLocked"]),
            )
        )
        return HandlingResult.success()
