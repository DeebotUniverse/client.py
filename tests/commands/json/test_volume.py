from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.commands.json import GetVolume, SetVolume
from deebot_client.commands.json.volume import NgiotGetVolume, NgiotSetVolume
from deebot_client.events import VolumeEvent
from deebot_client.exceptions import ApiError
from tests.helpers import get_request_json, get_success_body

from . import (
    assert_command,
    assert_ngiot_invalid_query_data,
    assert_ngiot_query,
    assert_ngiot_write_and_read_back,
    assert_set_command,
)

if TYPE_CHECKING:
    from unittest.mock import Mock

    from deebot_client.models import ApiDeviceInfo


async def test_GetVolume() -> None:
    json, firmware_event = get_request_json(
        get_success_body({"volume": 2, "total": 10})
    )
    await assert_command(GetVolume(), json, (firmware_event, VolumeEvent(2, 10)))


@pytest.mark.parametrize("level", [0, 2, 10])
async def test_SetVolume(level: int) -> None:
    args = {"volume": level}
    await assert_set_command(SetVolume(level), args, VolumeEvent(level, None))


@pytest.mark.parametrize("value", [0, 5])
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
        NgiotGetVolume(),
        "volume",
        value,
        VolumeEvent(value, 5),
        code,
    )


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"volume": None},
        {"volume": True},
        {"volume": -1},
        {"volume": 6},
        {"volume": "2"},
    ],
)
async def test_ngiot_invalid_query_data(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    data: dict[str, Any],
) -> None:
    await assert_ngiot_invalid_query_data(
        authenticator, api_device_info, event_bus_mock, NgiotGetVolume(), data
    )


@pytest.mark.parametrize(("requested", "reported"), [(0, 0), (5, 4)])
@pytest.mark.parametrize("code", [0, "0"])
async def test_ngiot_write_and_read_back(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    requested: int,
    reported: int,
    code: int | str,
) -> None:
    await assert_ngiot_write_and_read_back(
        authenticator,
        api_device_info,
        event_bus_mock,
        NgiotSetVolume(requested),
        "50023",
        "volume",
        requested,
        reported,
        VolumeEvent(reported, 5),
        code,
    )


async def test_ngiot_read_back_failure(
    authenticator: Mock, api_device_info: ApiDeviceInfo, event_bus_mock: Mock
) -> None:
    ack = {"body": {"code": 0, "msg": "ok"}}
    authenticator.post_ngiot.side_effect = [ack, ApiError("read failed")]

    result = await NgiotSetVolume(2).execute(
        authenticator, api_device_info, event_bus_mock
    )

    assert result.device_reached
    assert result.raw_response == ack
    assert authenticator.post_ngiot.await_count == 2
    event_bus_mock.notify.assert_not_called()


@pytest.mark.parametrize("volume", [-1, 6, True, 2.5, "2"])
def test_ngiot_invalid_volume(volume: Any) -> None:
    with pytest.raises(ValueError, match="Volume must be"):
        NgiotSetVolume(volume)
