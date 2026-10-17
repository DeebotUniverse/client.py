from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.commands.json.error import GetError
from deebot_client.events import (
    BorderSpinEvent,
    BorderSwitchEvent,
    CrossMapBorderWarningEvent,
    CutDirectionEvent,
    SafeProtectEvent,
)
from deebot_client.messages import get_message
from deebot_client.messages.json.battery import OnBattery
from deebot_client.messages.json.stats import OnStats
from tests.messages import assert_message

if TYPE_CHECKING:
    from deebot_client.events import Event
    from deebot_client.message import Message
    from deebot_client.models import StaticDeviceInfo


@pytest.mark.parametrize(
    ("device_class", "name", "expected"),
    [
        ("yna5xi", "onBattery", OnBattery),
        ("qhe2o2", "onBattery_V2", OnBattery),
        ("yna5xi", "onError", GetError),
        ("yna5xi", "onStats", OnStats),
        ("yna5xi", "GetCleanLogs", None),
        ("yna5xi", "unknown", None),
        ("2pv572", "unknown", None),
        ("xmp9ds", "onMapTrace", None),
        ("xmp9ds", "onMapSet", None),
        ("xmp9ds", "onMinorMap", None),
        ("xmp9ds", "onBattery", OnBattery),
    ],
)
def test_get_messages(
    static_device_info: StaticDeviceInfo, name: str, expected: type[Message] | None
) -> None:
    """Test get messages."""
    assert get_message(name, static_device_info) == expected


@pytest.mark.parametrize(
    ("device_class", "name", "data", "expected_event"),
    [
        pytest.param(
            "c9ej3j",
            "onBorderSpin",
            {"enable": 1, "type": 1},
            BorderSpinEvent(enabled=True),
            id="border_spin",
        ),
        pytest.param(
            "5xu9h3",
            "onBorderSwitch",
            {"enable": 0},
            BorderSwitchEvent(enabled=False),
            id="border_switch",
        ),
        pytest.param(
            "5xu9h3",
            "onCrossMapBorderWarning",
            {"enable": 1},
            CrossMapBorderWarningEvent(enabled=True),
            id="cross_map_border_warning",
        ),
        pytest.param(
            "5xu9h3",
            "onCutDirection",
            {"angle": 90},
            CutDirectionEvent(angle=90),
            id="cut_direction",
        ),
        pytest.param(
            "5xu9h3",
            "onSafeProtect",
            {"enable": 0},
            SafeProtectEvent(enabled=False),
            id="safe_protect",
        ),
    ],
)
def test_setting_push_messages(
    static_device_info: StaticDeviceInfo,
    device_class: str,
    name: str,
    data: dict[str, Any],
    expected_event: Event,
) -> None:
    """Test setting pushes are handled by the matching get command."""
    message = get_message(name, static_device_info)
    assert message is not None
    assert_message(
        message,
        {"header": {"ver": "0.0.1"}, "body": {"data": data}},
        expected_event,
        device_class=device_class,
    )
