"""Deebot T50 Max Pro Omni capabilities with verified station tank faults."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from deebot_client.capabilities import CapabilityEvent
from deebot_client.commands.json.error import GetError
from deebot_client.events import ErrorEvent
from deebot_client.hardware import elrxgb

if TYPE_CHECKING:
    from deebot_client.models import StaticDeviceInfo


def get_device_info() -> StaticDeviceInfo:
    """Extend the shared profile with verified water-tank fault support."""
    info = elrxgb.get_device_info()
    station = info.capabilities.station
    if station is None:
        raise ValueError("The shared hardware profile must have station capabilities")
    return replace(
        info,
        capabilities=replace(
            info.capabilities,
            station=replace(
                station, water_tank=CapabilityEvent(ErrorEvent, [GetError()])
            ),
        ),
    )
