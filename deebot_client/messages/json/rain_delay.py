"""Rain delay messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.rain_delay import RainDelayEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnRainDelay(MessageBodyDataDict):
    """Rain sensor configuration update."""

    NAME = "onRainDelay"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Notify subscribers with the reported rain sensor configuration."""
        event_bus.notify(
            RainDelayEvent(enabled=bool(data["enable"]), delay=int(data["delay"]))
        )
        return HandlingResult.success()
