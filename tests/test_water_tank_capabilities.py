"""Tests for source-independent station tank declarations."""

from __future__ import annotations

from dataclasses import replace

import pytest

from deebot_client.capabilities import (
    CapabilityEvent,
    CapabilityWaterTank,
    _get_events,
)
from deebot_client.events import ErrorEvent
from deebot_client.hardware import cuoipb


@pytest.mark.parametrize(
    ("clean", "dirty"), [(True, True), (True, False), (False, True), (False, False)]
)
def test_water_tank_support_does_not_change_event_refresh(
    clean: bool, dirty: bool
) -> None:
    """Per-tank support must not replace an event's own refresh declaration."""
    tank = CapabilityWaterTank(clean=clean, dirty=dirty)
    assert tank.clean is clean
    assert tank.dirty is dirty
    assert not _get_events(tank)

    capabilities = cuoipb.get_device_info().capabilities
    station = capabilities.station
    assert station is not None
    baseline = replace(
        capabilities,
        error=CapabilityEvent(ErrorEvent, []),
        station=replace(station, water_tank=None),
    )
    declared = replace(baseline, station=replace(station, water_tank=tank))
    assert declared._events == baseline._events
    assert declared.get_refresh_commands(ErrorEvent) == []
