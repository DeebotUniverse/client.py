from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.const import DataType
from deebot_client.messages import get_message
from deebot_client.messages.json import (
    OnBattery,
    OnChargeState,
    OnCleanInfo,
    OnCleanInfoV2,
    OnError,
    OnMapSetV2,
    OnMapTrace,
    OnMinorMap,
    OnPos,
    OnStats,
)

if TYPE_CHECKING:
    from deebot_client.message import Message


@pytest.mark.parametrize(
    ("name", "data_type", "expected"),
    [
        ("onBattery", DataType.JSON, OnBattery),
        ("onChargeState", DataType.JSON, OnChargeState),
        ("onCleanInfo", DataType.JSON, OnCleanInfo),
        ("onCleanInfo_V2", DataType.JSON, OnCleanInfoV2),
        ("onError", DataType.JSON, OnError),
        ("onMapSet_V2", DataType.JSON, OnMapSetV2),
        ("onMapTrace", DataType.JSON, OnMapTrace),
        ("onMinorMap", DataType.JSON, OnMinorMap),
        ("onPos", DataType.JSON, OnPos),
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
