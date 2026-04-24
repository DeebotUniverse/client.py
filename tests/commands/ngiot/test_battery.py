from __future__ import annotations

from unittest.mock import Mock

import pytest

from deebot_client.commands.ngiot.battery import GetBattery
from deebot_client.event_bus import EventBus
from deebot_client.events import AvailabilityEvent, BatteryEvent
from deebot_client.message import HandlingState


@pytest.mark.parametrize("battery", [0, 49, 100])
def test_get_battery_handles_available_battery(battery: int) -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetBattery.handle(event_bus, {"body": {"data": {"battery": battery}}})

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_any_call(AvailabilityEvent(available=True))
    event_bus.notify.assert_any_call(BatteryEvent(battery))


def test_get_battery_handles_missing_battery_as_unavailable() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetBattery.handle(event_bus, {"body": {"data": {}}})

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(AvailabilityEvent(available=False))
