from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from deebot_client.authentication import Authenticator
from deebot_client.commands.json.native_control import (
    NativeResetLifeSpan,
    NativeSetFanSpeed,
    NativeSetWaterAmount,
)
from deebot_client.event_bus import EventBus
from deebot_client.events import (
    FanSpeedEvent,
    FanSpeedLevel,
    LifeSpan,
    LifeSpanEvent,
)
from deebot_client.events.water_info import WaterAmount, WaterAmountEvent
from deebot_client.exceptions import DeebotError
from deebot_client.models import ApiDeviceInfo, Credentials
from tests.helpers import get_request_json, get_success_body

from . import assert_set_command


def _native_success() -> dict[str, Any]:
    return {
        "ret": "ok",
        "resp": {
            "header": {"fwVer": "10.0.9"},
            "body": {"code": 0, "msg": "ok"},
        },
    }


def _authenticator_mock() -> Mock:
    authenticator = Mock(spec_set=Authenticator)
    authenticator.authenticate = AsyncMock(
        return_value=Credentials("token", "user_id", 9999)
    )
    authenticator.post_authenticated = AsyncMock(return_value=_native_success())
    return authenticator


def _api_device_info() -> ApiDeviceInfo:
    return ApiDeviceInfo(
        {
            "company": "company",
            "did": "did",
            "name": "name",
            "nick": "nick",
            "resource": "resource",
            "class": "cqyi87",
        }
    )


@pytest.mark.parametrize(
    ("speed", "wire"),
    [
        (FanSpeedLevel.QUIET, "quiet"),
        (FanSpeedLevel.NORMAL, "auto"),
        (FanSpeedLevel.MAX, "strong"),
        (FanSpeedLevel.MAX_PLUS, "max"),
        ("quiet", "quiet"),
        ("normal", "auto"),
        ("max", "strong"),
        ("max_plus", "max"),
    ],
)
def test_native_fan_mapping(speed: FanSpeedLevel | str, wire: str) -> None:
    assert NativeSetFanSpeed(speed)._args == {"fanMode": wire}


@pytest.mark.parametrize(
    ("amount", "wire"),
    [
        (WaterAmount.LOW, "low"),
        (WaterAmount.MEDIUM, "mid"),
        (WaterAmount.HIGH, "high"),
        ("low", "low"),
        ("medium", "mid"),
        ("high", "high"),
    ],
)
def test_native_water_mapping(amount: WaterAmount | str, wire: str) -> None:
    assert NativeSetWaterAmount(amount)._args == {"waterMode": wire}


def test_native_fan_rejects_unknown_string() -> None:
    with pytest.raises(ValueError, match="not a valid FanSpeedLevel member"):
        NativeSetFanSpeed("turbo")


def test_native_water_rejects_ultrahigh() -> None:
    with pytest.raises(ValueError, match="Unsupported native water amount"):
        NativeSetWaterAmount(WaterAmount.ULTRAHIGH)


@pytest.mark.parametrize(
    ("native", "expected"),
    [
        ("quiet", FanSpeedLevel.QUIET),
        ("auto", FanSpeedLevel.NORMAL),
        ("strong", FanSpeedLevel.MAX),
        ("max", FanSpeedLevel.MAX_PLUS),
    ],
)
def test_native_fan_inverse_round_trip(native: str, expected: FanSpeedLevel) -> None:
    restored = NativeSetFanSpeed.create_from_mqtt(
        f'{{"body":{{"data":{{"fanMode": "{native}"}}}}}}'.encode()
    )
    assert restored == NativeSetFanSpeed(expected)
    assert restored._args == {"fanMode": native}


@pytest.mark.parametrize(
    ("native", "expected"),
    [
        ("low", WaterAmount.LOW),
        ("mid", WaterAmount.MEDIUM),
        ("high", WaterAmount.HIGH),
    ],
)
def test_native_water_inverse_round_trip(native: str, expected: WaterAmount) -> None:
    restored = NativeSetWaterAmount.create_from_mqtt(
        f'{{"body":{{"data":{{"waterMode": "{native}"}}}}}}'.encode()
    )
    assert restored == NativeSetWaterAmount(expected)


def test_native_fan_inverse_rejects_legacy_misread() -> None:
    # Native "max" means MAX_PLUS, never MAX.
    restored = NativeSetFanSpeed.create_from_mqtt(
        b'{"body":{"data":{"fanMode": "max"}}}'
    )
    assert restored == NativeSetFanSpeed(FanSpeedLevel.MAX_PLUS)
    assert restored != NativeSetFanSpeed(FanSpeedLevel.MAX)


def test_native_set_rejects_unknown_wire_value() -> None:
    with pytest.raises(DeebotError):
        NativeSetFanSpeed.create_from_mqtt(b'{"body":{"data":{"fanMode": "turbo"}}}')
    with pytest.raises(DeebotError):
        NativeSetWaterAmount.create_from_mqtt(
            b'{"body":{"data":{"waterMode": "ultra"}}}'
        )


async def test_native_set_fan_success_and_failure() -> None:
    await assert_set_command(
        NativeSetFanSpeed(FanSpeedLevel.MAX),
        {"fanMode": "strong"},
        FanSpeedEvent(FanSpeedLevel.MAX),
    )


async def test_native_set_water_success_and_failure() -> None:
    await assert_set_command(
        NativeSetWaterAmount(WaterAmount.MEDIUM),
        {"waterMode": "mid"},
        WaterAmountEvent(WaterAmount.MEDIUM),
    )


@pytest.mark.parametrize(
    ("life_span", "wire"),
    [
        (LifeSpan.BRUSH, "rollBrush"),
        (LifeSpan.FILTER, "filter"),
        (LifeSpan.SIDE_BRUSH, "sideBrush"),
        (LifeSpan.UNIT_CARE, "unitCare"),
    ],
)
def test_native_reset_mapping(life_span: LifeSpan, wire: str) -> None:
    command = NativeResetLifeSpan(life_span)
    assert command._args == {"resetConsumable": wire}
    assert command.NAME == "50017"


def test_native_reset_rejects_unsupported() -> None:
    with pytest.raises(ValueError, match="Unsupported native reset component"):
        NativeResetLifeSpan(LifeSpan.ROUND_MOP)


@pytest.mark.parametrize(
    ("native", "life_span"),
    [
        ("rollBrush", LifeSpan.BRUSH),
        ("filter", LifeSpan.FILTER),
        ("sideBrush", LifeSpan.SIDE_BRUSH),
        ("unitCare", LifeSpan.UNIT_CARE),
    ],
)
def test_native_reset_mqtt_round_trip(native: str, life_span: LifeSpan) -> None:
    restored = NativeResetLifeSpan.create_from_mqtt(
        f'{{"body":{{"data":{{"resetConsumable": "{native}"}}}}}}'.encode()
    )
    assert restored == NativeResetLifeSpan(life_span)
    assert restored._args == {"resetConsumable": native}


def test_native_reset_filter_sends_native_name_not_heap() -> None:
    command = NativeResetLifeSpan(LifeSpan.FILTER)
    assert command._args == {"resetConsumable": "filter"}


def test_native_reset_rejects_unknown_component() -> None:
    with pytest.raises(DeebotError):
        NativeResetLifeSpan.create_from_mqtt(
            b'{"body":{"data":{"resetConsumable": "mop"}}}'
        )


async def test_native_reset_success_refreshes_failed_does_not() -> None:
    consumables, _ = get_request_json(
        get_success_body(
            {"consumables": [{"type": "sideBrush", "left": 8977, "total": 9000}]}
        )
    )
    event_bus = Mock(spec_set=EventBus)
    authenticator = _authenticator_mock()
    authenticator.post_authenticated = AsyncMock(
        side_effect=[_native_success(), consumables]
    )

    await NativeResetLifeSpan(LifeSpan.SIDE_BRUSH).execute(
        authenticator, _api_device_info(), event_bus
    )
    assert authenticator.post_authenticated.call_count == 2
    event_bus.notify.assert_called_with(LifeSpanEvent(LifeSpan.SIDE_BRUSH, 99.74, 8977))

    authenticator_fail = _authenticator_mock()
    authenticator_fail.post_authenticated = AsyncMock(
        return_value={
            "ret": "ok",
            "resp": {"header": {}, "body": {"code": 500, "msg": "fail"}},
        }
    )
    event_bus_fail = Mock(spec_set=EventBus)
    await NativeResetLifeSpan(LifeSpan.SIDE_BRUSH).execute(
        authenticator_fail, _api_device_info(), event_bus_fail
    )
    assert authenticator_fail.post_authenticated.call_count == 1
    event_bus_fail.notify.assert_not_called()
