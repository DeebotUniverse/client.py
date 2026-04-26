from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest

from deebot_client.commands.ngiot.common import APN_FAN_MODE
from deebot_client.commands.ngiot.fan_speed import GetFanSpeed, SetFanSpeed
from deebot_client.event_bus import EventBus
from deebot_client.events import FanSpeedEvent, FanSpeedLevel
from deebot_client.message import HandlingState
from deebot_client.models import ApiDeviceInfo
from deebot_client.ngiot_client import NgiotClient, NgiotRequest


def _api_device() -> ApiDeviceInfo:
    return cast(
        ApiDeviceInfo,
        {
            "did": "did-1",
            "class": "eyfj07",
            "company": "eco",
            "name": "robot",
            "resource": "res-1",
        },
    )


@pytest.mark.parametrize(
    ("wire_value", "expected"),
    [
        ("quiet", FanSpeedLevel.QUIET),
        ("auto", FanSpeedLevel.NORMAL),
        ("strong", FanSpeedLevel.MAX),
        ("max", FanSpeedLevel.MAX_PLUS),
    ],
)
def test_get_fan_speed_maps_wire_values(
    wire_value: str,
    expected: FanSpeedLevel,
) -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetFanSpeed.handle(
        cast(EventBus, event_bus),
        {"body": {"data": {"fanMode": wire_value}}},
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(FanSpeedEvent(expected))


def test_get_fan_speed_unknown_value_requests_analysis() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetFanSpeed.handle(
        cast(EventBus, event_bus),
        {"body": {"data": {"fanMode": "unsupported"}}},
    )

    assert result.state == HandlingState.ANALYSE_LOGGED
    event_bus.notify.assert_not_called()


@pytest.mark.parametrize(
    ("speed", "wire_value"),
    [
        (FanSpeedLevel.QUIET, "quiet"),
        (FanSpeedLevel.NORMAL, "auto"),
        (FanSpeedLevel.MAX, "strong"),
        (FanSpeedLevel.MAX_PLUS, "max"),
    ],
)
async def test_set_fan_speed_uses_write_apn(
    speed: FanSpeedLevel,
    wire_value: str,
) -> None:
    client_mock = AsyncMock(spec_set=NgiotClient)
    client_mock.request.return_value = {"body": {"code": 0, "msg": "ok"}}
    device_info = _api_device()

    response = await SetFanSpeed(speed)._request_ngiot(
        cast(NgiotClient, client_mock),
        device_info,
    )

    assert response == {"body": {"code": 0, "msg": "ok"}}
    client_mock.request.assert_awaited_once_with(
        device_info,
        NgiotRequest(apn=APN_FAN_MODE, body_data={"fanMode": wire_value}),
    )


def test_set_fan_speed_notifies_event_after_success() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = SetFanSpeed(FanSpeedLevel.MAX)._handle_response(
        cast(EventBus, event_bus),
        {"ret": "ok", "resp": {"body": {"code": 0, "msg": "ok"}}},
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(FanSpeedEvent(FanSpeedLevel.MAX))