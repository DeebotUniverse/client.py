"""(fan) speed commands."""
from types import MappingProxyType
from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events import FanSpeedEvent, FanSpeedLevel
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import JsonCommandWithMessageHandling, JsonSetCommand


class GetFanSpeed(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get fan speed command."""

    name = "getSpeed"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(FanSpeedEvent(FanSpeedLevel(int(data["speed"]))))
        return HandlingResult.success()


class SetFanSpeed(JsonSetCommand):
    """Set fan speed command."""

    name = "setSpeed"
    get_command = GetFanSpeed
    _mqtt_params = MappingProxyType({"speed": InitParam(FanSpeedLevel)})

    def __init__(self, speed: FanSpeedLevel | str) -> None:
        if isinstance(speed, str):
            speed = FanSpeedLevel.get(speed)
        super().__init__({"speed": speed.value})
