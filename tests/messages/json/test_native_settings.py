from __future__ import annotations

from typing import Any
from unittest.mock import Mock, call

import pytest

from deebot_client.capabilities import CapabilitySetEnable, CapabilitySettings
from deebot_client.event_bus import EventBus
from deebot_client.events import (
    CarpetAutoFanBoostEvent,
    ChildLockEvent,
    ContinuousCleaningEvent,
    DoNotDisturbEvent,
    EnableEvent,
    VolumeEvent,
)
from deebot_client.messages.json.native_settings import (
    handle_native_settings,
)


def test_helper_handles_all_five_fields_live_confirmed() -> None:
    event_bus = Mock(spec_set=EventBus)
    data: dict[str, Any] = {
        "childLock": False,
        "autoBoost": True,
        "breakCleanSwitch": True,
        "disturbSwitch": True,
        "volume": 10,
    }
    handle_native_settings(event_bus, data)
    expected_calls = [
        call(ChildLockEvent(False)),
        call(CarpetAutoFanBoostEvent(True)),
        call(ContinuousCleaningEvent(True)),
        call(DoNotDisturbEvent(True)),
        call(VolumeEvent(10, 10)),
    ]
    event_bus.notify.assert_has_calls(expected_calls, any_order=True)
    assert event_bus.notify.call_count == 5


def test_helper_handles_all_five_fields_inverted() -> None:
    event_bus = Mock(spec_set=EventBus)
    data: dict[str, Any] = {
        "childLock": True,
        "autoBoost": False,
        "breakCleanSwitch": False,
        "disturbSwitch": False,
        "volume": 0,
    }
    handle_native_settings(event_bus, data)
    expected_calls = [
        call(ChildLockEvent(True)),
        call(CarpetAutoFanBoostEvent(False)),
        call(ContinuousCleaningEvent(False)),
        call(DoNotDisturbEvent(False)),
        call(VolumeEvent(0, 10)),
    ]
    event_bus.notify.assert_has_calls(expected_calls, any_order=True)
    assert event_bus.notify.call_count == 5


@pytest.mark.parametrize(
    ("payload", "expected_event"),
    [
        ({"childLock": True}, ChildLockEvent(True)),
        ({"childLock": False}, ChildLockEvent(False)),
        ({"autoBoost": True}, CarpetAutoFanBoostEvent(True)),
        ({"autoBoost": False}, CarpetAutoFanBoostEvent(False)),
        ({"breakCleanSwitch": True}, ContinuousCleaningEvent(True)),
        ({"breakCleanSwitch": False}, ContinuousCleaningEvent(False)),
        ({"disturbSwitch": True}, DoNotDisturbEvent(True)),
        ({"disturbSwitch": False}, DoNotDisturbEvent(False)),
        ({"volume": 0}, VolumeEvent(0, 10)),
        ({"volume": 5}, VolumeEvent(5, 10)),
        ({"volume": 10}, VolumeEvent(10, 10)),
    ],
)
def test_helper_partial_no_invented_defaults(
    payload: dict[str, Any], expected_event: Any
) -> None:
    event_bus = Mock(spec_set=EventBus)
    handle_native_settings(event_bus, payload)
    event_bus.notify.assert_called_once_with(expected_event)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"unknownField": 123},
        {"childLock": 1},
        {"childLock": "true"},
        {"childLock": None},
        {"autoBoost": 0},
        {"autoBoost": "false"},
        {"breakCleanSwitch": 1},
        {"breakCleanSwitch": "yes"},
        {"disturbSwitch": 0},
        {"disturbSwitch": "no"},
        {"volume": True},
        {"volume": False},
        {"volume": -1},
        {"volume": 11},
        {"volume": "10"},
        {"volume": 5.5},
        {"volume": None},
    ],
)
def test_helper_ignores_absent_unknown_malformed(payload: dict[str, Any]) -> None:
    event_bus = Mock(spec_set=EventBus)
    handle_native_settings(event_bus, payload)
    event_bus.notify.assert_not_called()


def test_do_not_disturb_event_contract() -> None:
    event_true = DoNotDisturbEvent(True)
    assert event_true.enabled is True
    assert isinstance(event_true, EnableEvent)

    event_false = DoNotDisturbEvent(False)
    assert event_false.enabled is False
    assert isinstance(event_false, EnableEvent)


def test_capability_settings_default_none() -> None:
    settings = CapabilitySettings()
    assert settings.do_not_disturb is None
    assert settings.child_lock is None
    assert settings.volume is None
    assert settings.carpet_auto_fan_boost is None

    get_cmd = Mock()
    set_cmd = Mock()
    cap = CapabilitySetEnable(DoNotDisturbEvent, [get_cmd], set_cmd)
    custom_settings = CapabilitySettings(do_not_disturb=cap)
    assert custom_settings.do_not_disturb is cap
