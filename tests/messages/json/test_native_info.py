from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, call

import pytest

from deebot_client.capabilities import Capabilities
from deebot_client.event_bus import EventBus
from deebot_client.events import BatteryEvent, FirmwareEvent, StateEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json.native_info import NativeInfoEvent, OnNativeInfo
from deebot_client.models import State
from tests.messages import assert_message_failure
from tests.messages.json import assert_message


def _report(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "header": {
            "pri": 3,
            "m": "cloudctl",
            "channel": "rop",
            "ver": "0.0.9",
            "fwVer": "10.0.9",
            "hwVer": "1.2.0",
            "tzm": 480,
            "ts": "1791717778000",
        },
        "body": {"data": data},
    }


@pytest.mark.parametrize("status", ["smartClean", "areaClean", "zoneClean"])
def test_cleaning_report(status: str) -> None:
    assert_message(
        OnNativeInfo,
        _report({"status": status, "pauseSwitch": False}),
        (
            FirmwareEvent("10.0.9"),
            StateEvent(State.CLEANING),
            NativeInfoEvent(status=status, charge_status=None, pause_switch=False),
        ),
    )


def test_paused_report() -> None:
    assert_message(
        OnNativeInfo,
        _report({"status": "smartClean", "pauseSwitch": True}),
        (
            FirmwareEvent("10.0.9"),
            StateEvent(State.PAUSED),
            NativeInfoEvent(status="smartClean", charge_status=None, pause_switch=True),
        ),
    )


def test_returning_report() -> None:
    assert_message(
        OnNativeInfo,
        _report({"status": "goCharge", "pauseSwitch": False}),
        (
            FirmwareEvent("10.0.9"),
            StateEvent(State.RETURNING),
            NativeInfoEvent(status="goCharge", charge_status=None, pause_switch=False),
        ),
    )


def test_docked_report() -> None:
    assert_message(
        OnNativeInfo,
        _report({"status": "idle", "chargeStatus": True}),
        (
            FirmwareEvent("10.0.9"),
            StateEvent(State.DOCKED),
            NativeInfoEvent(status="idle", charge_status=True, pause_switch=None),
        ),
    )


def test_battery_only_keeps_state() -> None:
    # Fields-only update: no StateEvent, no NativeInfoEvent, only battery.
    assert_message(
        OnNativeInfo,
        _report({"battery": 100}),
        (FirmwareEvent("10.0.9"), BatteryEvent(100)),
    )


def test_status_only_keeps_state_no_invented_pause() -> None:
    # status alone without pause history must not invent CLEANING/PAUSED.
    assert_message(
        OnNativeInfo,
        _report({"status": "smartClean"}),
        (
            FirmwareEvent("10.0.9"),
            NativeInfoEvent(status="smartClean", charge_status=None, pause_switch=None),
        ),
    )


def test_empty_unknown_malformed_no_defaults() -> None:
    assert_message(OnNativeInfo, _report({}), FirmwareEvent("10.0.9"))
    assert_message(OnNativeInfo, _report({"unknownField": 1}), FirmwareEvent("10.0.9"))
    assert_message(OnNativeInfo, _report({"status": "none"}), FirmwareEvent("10.0.9"))
    assert_message_failure(
        OnNativeInfo,
        _report({"battery": "full"}),
        HandlingState.ANALYSE_LOGGED,
        FirmwareEvent("10.0.9"),
    )
    assert_message_failure(
        OnNativeInfo,
        _report({"battery": True}),
        HandlingState.ANALYSE_LOGGED,
        FirmwareEvent("10.0.9"),
    )
    assert_message_failure(
        OnNativeInfo,
        _report({"battery": 101}),
        HandlingState.ANALYSE_LOGGED,
        FirmwareEvent("10.0.9"),
    )
    assert_message_failure(
        OnNativeInfo,
        _report({"battery": -1}),
        HandlingState.ANALYSE_LOGGED,
        FirmwareEvent("10.0.9"),
    )


def test_unknown_status_clears_cache_no_stale_pause() -> None:
    bus = Mock(spec_set=EventBus)
    bus.get_last_event.return_value = NativeInfoEvent(
        status="smartClean", charge_status=False, pause_switch=False
    )
    result = OnNativeInfo.handle(bus, _report({"status": "stuck"}))
    assert result.state == HandlingState.SUCCESS
    bus.notify.assert_has_calls(
        [
            call(FirmwareEvent("10.0.9")),
            call(NativeInfoEvent(status=None, charge_status=False, pause_switch=False)),
        ]
    )
    assert bus.notify.call_count == 2

    bus.get_last_event.return_value = NativeInfoEvent(
        status=None, charge_status=False, pause_switch=False
    )
    bus.reset_mock()
    result = OnNativeInfo.handle(bus, _report({"pauseSwitch": True}))
    assert result.state == HandlingState.SUCCESS
    assert bus.notify.call_count == 2
    bus.notify.assert_has_calls(
        [
            call(FirmwareEvent("10.0.9")),
            call(NativeInfoEvent(status=None, charge_status=False, pause_switch=True)),
        ]
    )


def test_pause_only_merges_per_bus_no_global_state() -> None:
    bus_clean = Mock(spec_set=EventBus)
    bus_clean.get_last_event.return_value = NativeInfoEvent(
        status="smartClean", charge_status=False, pause_switch=False
    )
    result = OnNativeInfo.handle(bus_clean, _report({"pauseSwitch": True}))
    assert result.state == HandlingState.SUCCESS
    bus_clean.notify.assert_has_calls(
        [
            call(FirmwareEvent("10.0.9")),
            call(StateEvent(State.PAUSED)),
            call(
                NativeInfoEvent(
                    status="smartClean", charge_status=False, pause_switch=True
                )
            ),
        ]
    )
    assert bus_clean.notify.call_count == 3

    bus_fresh = Mock(spec_set=EventBus)
    bus_fresh.get_last_event.return_value = None
    result = OnNativeInfo.handle(bus_fresh, _report({"pauseSwitch": True}))
    assert result.state == HandlingState.SUCCESS
    # No status history: must not invent PAUSED/CLEANING, only cache merge.
    assert bus_fresh.notify.call_count == 2
    bus_fresh.notify.assert_has_calls(
        [
            call(FirmwareEvent("10.0.9")),
            call(NativeInfoEvent(status=None, charge_status=None, pause_switch=True)),
        ]
    )


def test_real_event_bus_sequential_merge_and_isolation() -> None:
    def _bus() -> EventBus:
        capabilities = Mock(spec_set=Capabilities)
        capabilities.get_refresh_commands.return_value = []
        return EventBus(AsyncMock(), capabilities)

    bus_a = _bus()
    bus_b = _bus()
    OnNativeInfo.handle(bus_a, _report({"status": "smartClean", "pauseSwitch": False}))
    assert bus_a.get_last_event(StateEvent) == StateEvent(State.CLEANING)
    # Second bus untouched: isolation.
    assert bus_b.get_last_event(StateEvent) is None
    assert bus_b.get_last_event(NativeInfoEvent) is None
    # Partial pause-only report merges with bus_a cache.
    OnNativeInfo.handle(bus_a, _report({"pauseSwitch": True}))
    assert bus_a.get_last_event(StateEvent) == StateEvent(State.PAUSED)
    assert bus_b.get_last_event(StateEvent) is None
