from __future__ import annotations

from typing import Any
from unittest.mock import Mock, call

import pytest

from deebot_client.event_bus import EventBus
from deebot_client.events import (
    BatteryEvent,
    ErrorEvent,
    FanSpeedEvent,
    FanSpeedLevel,
    FirmwareEvent,
    LifeSpan,
    LifeSpanEvent,
    NetworkInfoEvent,
    StateEvent,
    StatsEvent,
)
from deebot_client.events.water_info import (
    MopAttachedEvent,
    WaterAmount,
    WaterAmountEvent,
)
from deebot_client.message import HandlingState
from deebot_client.messages.json.native_info import NativeInfoEvent, OnNativeInfo
from deebot_client.models import State
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


def test_fan_water_mop_mapping() -> None:
    assert_message(
        OnNativeInfo,
        _report({"fanMode": "max", "waterMode": "mid", "mopState": "installed"}),
        (
            FirmwareEvent("10.0.9"),
            FanSpeedEvent(FanSpeedLevel.MAX_PLUS),
            WaterAmountEvent(WaterAmount.MEDIUM),
            MopAttachedEvent(True),
        ),
    )


def test_mop_state_unknown_ignored() -> None:
    assert_message(
        OnNativeInfo, _report({"mopState": "unknown"}), FirmwareEvent("10.0.9")
    )


def test_consumables_full_list() -> None:
    assert_message(
        OnNativeInfo,
        _report(
            {
                "consumables": [
                    {"type": "rollBrush", "left": 17979, "total": 18000},
                    {"type": "filter", "left": 7179, "total": 7200},
                    {"type": "sideBrush", "left": 8977, "total": 9000},
                    {"type": "unitCare", "left": 265, "total": 1800},
                ]
            }
        ),
        (
            FirmwareEvent("10.0.9"),
            LifeSpanEvent(LifeSpan.BRUSH, 99.88, 17979),
            LifeSpanEvent(LifeSpan.FILTER, 99.71, 7179),
            LifeSpanEvent(LifeSpan.SIDE_BRUSH, 99.74, 8977),
            LifeSpanEvent(LifeSpan.UNIT_CARE, 14.72, 265),
        ),
    )


def test_consumables_invalid_entries_skipped() -> None:
    assert_message(
        OnNativeInfo,
        _report(
            {
                "consumables": [
                    {"type": "rollBrush", "left": 0, "total": 0},
                    {"type": "mop", "left": 10, "total": 100},
                    {"type": "filter", "left": "full", "total": 7200},
                    {"type": "sideBrush", "left": 8977, "total": 9000},
                    "broken",
                ]
            }
        ),
        (
            FirmwareEvent("10.0.9"),
            LifeSpanEvent(LifeSpan.SIDE_BRUSH, 99.74, 8977),
        ),
    )
    assert_message(
        OnNativeInfo, _report({"consumables": "full"}), FirmwareEvent("10.0.9")
    )
    assert_message(OnNativeInfo, _report({"consumables": []}), FirmwareEvent("10.0.9"))


def test_device_info_full_report() -> None:
    assert_message(
        OnNativeInfo,
        _report(
            {
                "deviceInfo": {
                    "ip": "192.0.2.10",
                    "ssid": "TestNet",
                    "mac": "AA:BB:CC:DD:EE:FF",
                    "rssi": "-55.7",
                    "fwVersion": "10.0.9",
                    "sn": "ignored",
                }
            }
        ),
        (
            FirmwareEvent("10.0.9"),
            NetworkInfoEvent(
                ip="192.0.2.10", ssid="TestNet", rssi=-55, mac="AA:BB:CC:DD:EE:FF"
            ),
        ),
    )


def test_device_info_partial_merges_with_history() -> None:
    bus = Mock(spec_set=EventBus)
    prior = NetworkInfoEvent(
        ip="192.0.2.10", ssid="TestNet", rssi=-55, mac="AA:BB:CC:DD:EE:FF"
    )
    bus.get_last_event.return_value = prior
    result = OnNativeInfo.handle(bus, _report({"deviceInfo": {"rssi": "-60"}}))
    assert result.state == HandlingState.SUCCESS
    bus.notify.assert_has_calls(
        [
            call(FirmwareEvent("10.0.9")),
            call(
                NetworkInfoEvent(
                    ip="192.0.2.10",
                    ssid="TestNet",
                    rssi=-60,
                    mac="AA:BB:CC:DD:EE:FF",
                )
            ),
        ]
    )
    assert bus.notify.call_count == 2


def test_device_info_partial_without_history_emits_nothing() -> None:
    assert_message(
        OnNativeInfo,
        _report({"deviceInfo": {"rssi": "-60"}}),
        FirmwareEvent("10.0.9"),
    )
    assert_message(
        OnNativeInfo, _report({"deviceInfo": "none"}), FirmwareEvent("10.0.9")
    )


@pytest.mark.parametrize(
    ("codes", "code", "description"),
    [
        ((0,), 0, "No error"),
        ((102,), 102, "Robot is lifted"),
        ((111,), 111, "Bumper is stuck"),
        ((0, 102), 102, "Robot is lifted"),
        ((102, 111), 111, "Bumper is stuck"),
        ((), 0, "No error"),
        ((991,), 991, None),
    ],
)
def test_native_error_description_without_state_change(
    codes: tuple[int, ...], code: int, description: str | None
) -> None:
    assert_message(
        OnNativeInfo,
        _report({"error": list(codes)}),
        (FirmwareEvent("10.0.9"), ErrorEvent(code, description)),
    )


@pytest.mark.parametrize("codes", [[], [0]])
async def test_native_error_clear_replaces_prior_error(
    event_bus: EventBus, codes: list[int]
) -> None:
    # Given: a previously reported native fault.
    OnNativeInfo.handle(event_bus, _report({"error": [102]}))

    # When: the robot reports no active errors.
    OnNativeInfo.handle(event_bus, _report({"error": codes}))

    # Then: subscribers' cached error is cleared, not left stale.
    assert event_bus.get_last_event(ErrorEvent) == ErrorEvent(0, "No error")


@pytest.mark.parametrize("value", [None, "none", [True], ["102"], [102.0]])
async def test_invalid_native_error_preserves_prior_error(
    event_bus: EventBus, value: list[int | float | str] | str | None
) -> None:
    OnNativeInfo.handle(event_bus, _report({"error": [111]}))
    before = event_bus.get_last_event(ErrorEvent)
    assert before is not None

    OnNativeInfo.handle(event_bus, _report({"error": value}))

    assert event_bus.get_last_event(ErrorEvent) == before


async def test_missing_native_error_preserves_prior_error(event_bus: EventBus) -> None:
    OnNativeInfo.handle(event_bus, _report({"error": [102]}))
    before = event_bus.get_last_event(ErrorEvent)
    assert before is not None

    OnNativeInfo.handle(event_bus, _report({"battery": 87}))

    assert event_bus.get_last_event(ErrorEvent) == before


def test_clean_area_current_only() -> None:
    assert_message(
        OnNativeInfo,
        _report({"cleanArea": 125}),
        (FirmwareEvent("10.0.9"), StatsEvent(area=125, time=None, type=None)),
    )
    assert_message(OnNativeInfo, _report({"cleanArea": True}), FirmwareEvent("10.0.9"))
    assert_message(OnNativeInfo, _report({"cleanArea": "125"}), FirmwareEvent("10.0.9"))


def test_full_telemetry_report() -> None:
    assert_message(
        OnNativeInfo,
        _report(
            {
                "status": "smartClean",
                "pauseSwitch": False,
                "battery": 87,
                "fanMode": "max",
                "waterMode": "mid",
                "mopState": "installed",
                "consumables": [{"type": "filter", "left": 7179, "total": 7200}],
                "deviceInfo": {
                    "ip": "192.0.2.10",
                    "ssid": "TestNet",
                    "mac": "AA:BB:CC:DD:EE:FF",
                    "rssi": -55,
                },
                "error": [0],
                "cleanArea": 125,
            }
        ),
        (
            FirmwareEvent("10.0.9"),
            BatteryEvent(87),
            FanSpeedEvent(FanSpeedLevel.MAX_PLUS),
            WaterAmountEvent(WaterAmount.MEDIUM),
            MopAttachedEvent(True),
            LifeSpanEvent(LifeSpan.FILTER, 99.71, 7179),
            NetworkInfoEvent(
                ip="192.0.2.10", ssid="TestNet", rssi=-55, mac="AA:BB:CC:DD:EE:FF"
            ),
            ErrorEvent(0, "No error"),
            StatsEvent(area=125, time=None, type=None),
            StateEvent(State.CLEANING),
            NativeInfoEvent(
                status="smartClean", charge_status=None, pause_switch=False
            ),
        ),
    )
