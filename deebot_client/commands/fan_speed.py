"""(fan) speed commands."""
from typing import Any, Mapping, Union

from ..events import FanSpeedEvent
from ..message import HandlingResult
from ..util import DisplayNameIntEnum
from .common import EventBus, SetCommand, _NoArgsCommand


class FanSpeedLevel(DisplayNameIntEnum):
    """Enum class for all possible fan speed levels."""

    # Values should be sort from low to high on their meanings
    QUIET = 1000
    NORMAL = 0
    MAX = 1
    MAX_PLUS = 2, "max+"


class GetFanSpeed(_NoArgsCommand):
    """Get fan speed command."""

    name = "getSpeed"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(FanSpeedEvent(FanSpeedLevel(int(data["speed"])).display_name))
        return HandlingResult.success()


class SetFanSpeed(SetCommand):
    """Set fan speed command."""

    name = "setSpeed"
    get_command = GetFanSpeed

    def __init__(
        self, speed: Union[str, int, FanSpeedLevel], **kwargs: Mapping[str, Any]
    ) -> None:
        if isinstance(speed, str):
            speed = FanSpeedLevel.get(speed)
        if isinstance(speed, FanSpeedLevel):
            speed = speed.value

        super().__init__({"speed": speed}, **kwargs)
