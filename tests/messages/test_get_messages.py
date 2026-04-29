from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.capabilities import DeviceType
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.map import GetMapSet, GetMapTrace, GetMinorMap
from deebot_client.const import DataType
from deebot_client.messages import get_message
from deebot_client.messages.json.battery import OnBattery
from deebot_client.messages.json.stats import OnStats

if TYPE_CHECKING:
    from deebot_client.message import Message


@pytest.mark.parametrize(
    ("name", "data_type", "expected"),
    [
        ("onBattery", DataType.JSON, OnBattery),
        ("onBattery_V2", DataType.JSON, OnBattery),
        ("onError", DataType.JSON, GetError),
        ("onStats", DataType.JSON, OnStats),
        ("GetCleanLogs", DataType.JSON, None),
        ("unknown", DataType.JSON, None),
        ("unknown", DataType.XML, None),
    ],
)
def test_get_messages(
    name: str, data_type: DataType, expected: type[Message] | None
) -> None:
    """Test get messages."""
    assert get_message(name, data_type) == expected


@pytest.mark.parametrize(
    ("name", "device_type", "expected"),
    [
        # No device type => legacy fallback returns the command class
        # (preserves existing behaviour).
        ("onMapTrace", None, GetMapTrace),
        # Vacuums consume map trace pushes — fallback still applies.
        ("onMapTrace", DeviceType.VACUUM, GetMapTrace),
        ("onMapSet", DeviceType.VACUUM, GetMapSet),
        ("onMinorMap", DeviceType.VACUUM, GetMinorMap),
        # Mowers do not expose a `map=` capability, so spontaneous
        # map pushes from the firmware would only spam "Could not parse"
        # warnings. Skip the legacy fallback for them.
        ("onMapTrace", DeviceType.MOWER, None),
        ("onMapSet", DeviceType.MOWER, None),
        ("onMinorMap", DeviceType.MOWER, None),
        # Non-map messages remain unaffected on either device type.
        ("onBattery", DeviceType.MOWER, OnBattery),
        ("onBattery", DeviceType.VACUUM, OnBattery),
        ("onError", DeviceType.MOWER, GetError),
    ],
)
def test_get_messages_device_type_filter(
    name: str,
    device_type: DeviceType | None,
    expected: type[Message] | None,
) -> None:
    """Skip map-related legacy fallbacks for mowers; preserve everything else."""
    assert get_message(name, DataType.JSON, device_type) == expected
