"""Battery commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import AvailabilityEvent, BatteryEvent
from deebot_client.message import HandlingResult

from .common import RobotDetailGetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetBattery(RobotDetailGetCommand):
    """Get battery percentage."""

    NAME = "getBattery"
    FIELDS = ("battery",)

    def __init__(self, *, is_available_check: bool = False) -> None:
        super().__init__(is_available_check=is_available_check)

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus: EventBus,
        data: dict[str, Any],
    ) -> HandlingResult:
        battery = data.get("battery")
        available = battery is not None
        event_bus.notify(AvailabilityEvent(available=available))
        if available:
            event_bus.notify(BatteryEvent(int(battery)))
        return HandlingResult.success()