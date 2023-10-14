"""(fan) speed commands."""
from typing import Any

from deebot_client.command import InitParam
from deebot_client.events import FanSpeedEvent, FanSpeedLevel
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import CommandWithMessageHandling, EventBus, SetCommand


class GetFanSpeed(CommandWithMessageHandling, MessageBodyDataDict):
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


class SetFanSpeed(SetCommand):
    """Set fan speed command."""

    name = "setSpeed"
    get_command = GetFanSpeed
    _mqtt_params = {"speed": InitParam("speed", FanSpeedLevel)}

    def __init__(self, speed: FanSpeedLevel) -> None:
        super().__init__({"speed": speed.value})
