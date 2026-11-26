from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.commands.json import GetBattery
from deebot_client.commands.json.battery import NgiotGetBattery
from deebot_client.events import BatteryEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_ngiot_invalid_query_data, assert_ngiot_query

if TYPE_CHECKING:
    from unittest.mock import Mock

    from deebot_client.models import ApiDeviceInfo


@pytest.mark.parametrize("percentage", [0, 49, 100])
async def test_GetBattery(percentage: int) -> None:
    json, firmware_event = get_request_json(
        get_success_body({"value": percentage, "isLow": 1 if percentage < 20 else 0})
    )
    await assert_command(GetBattery(), json, (firmware_event, BatteryEvent(percentage)))


@pytest.mark.parametrize("value", [0, 100])
@pytest.mark.parametrize("code", [0, "0"])
async def test_ngiot_query(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    value: int,
    code: int | str,
) -> None:
    await assert_ngiot_query(
        authenticator,
        api_device_info,
        event_bus_mock,
        NgiotGetBattery(),
        "battery",
        value,
        BatteryEvent(value),
        code,
    )


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"battery": None},
        {"battery": True},
        {"battery": -1},
        {"battery": 101},
        {"battery": "100"},
    ],
)
async def test_ngiot_invalid_query_data(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    data: dict[str, Any],
) -> None:
    await assert_ngiot_invalid_query_data(
        authenticator, api_device_info, event_bus_mock, NgiotGetBattery(), data
    )


@pytest.mark.parametrize("body", [{"code": 0}, {"code": 0, "data": []}])
async def test_ngiot_missing_query_data(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    body: dict[str, Any],
) -> None:
    authenticator.post_ngiot.return_value = {"body": body}

    result = await NgiotGetBattery().execute(
        authenticator, api_device_info, event_bus_mock
    )

    assert not result.device_reached
    event_bus_mock.notify.assert_not_called()
