"""(fan) speed commands."""
from collections.abc import Mapping
from typing import Any

from ..events import FanSpeedEvent, FanSpeedLevel
from ..message import HandlingResult, MessageBodyDataDict
from .common import EventBus, NoArgsCommand, SetCommand


class GetFanSpeed(NoArgsCommand, MessageBodyDataDict):
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

    def __init__(
        self, speed: str | int | FanSpeedLevel, **kwargs: Mapping[str, Any]
    ) -> None:
        if isinstance(speed, str):
            speed = FanSpeedLevel.get(speed)
        if isinstance(speed, FanSpeedLevel):
            speed = speed.value

        super().__init__({"speed": speed}, **kwargs)
