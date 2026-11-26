"""Battery commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import BatteryEvent
from deebot_client.message import HandlingResult
from deebot_client.messages.json import OnBattery

from .common import JsonCommandWithMessageHandling, JsonGetCommand, NgiotJsonCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetBattery(OnBattery, JsonCommandWithMessageHandling):
    """Get battery command."""

    NAME = "getBattery"

    def __init__(self, *, is_available_check: bool = False) -> None:
        super().__init__()
        self._is_available_check = is_available_check


class NgiotGetBattery(NgiotJsonCommand, JsonGetCommand):
    """Get battery percentage through NGIOT."""

    NAME = "ngiotGetBattery"
    APN = "10001"

    def __init__(self, *, is_available_check: bool = False) -> None:
        super().__init__({"fields": ["battery"]})
        self._is_available_check = is_available_check

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        battery = data.get("battery")
        if (
            not isinstance(battery, int)
            or isinstance(battery, bool)
            or not 0 <= battery <= 100
        ):
            return HandlingResult.analyse()

        event_bus.notify(BatteryEvent(battery))
        return HandlingResult.success()
