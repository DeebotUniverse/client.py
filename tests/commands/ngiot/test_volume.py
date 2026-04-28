from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, Mock

import pytest

from deebot_client.commands.ngiot.common import APN_SET_VOLUME
from deebot_client.commands.ngiot.volume import GetVolume, SetVolume
from deebot_client.event_bus import EventBus
from deebot_client.events import VolumeEvent
from deebot_client.message import HandlingState
from deebot_client.ngiot_client import NgiotClient, NgiotRequest

if TYPE_CHECKING:
    from deebot_client.models import ApiDeviceInfo


def _api_device() -> ApiDeviceInfo:
    return cast(
        "ApiDeviceInfo",
        {
            "did": "did-1",
            "class": "eyfj07",
            "company": "eco",
            "name": "robot",
            "resource": "res-1",
        },
    )


def test_get_volume_notifies_event() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetVolume.handle(
        cast("EventBus", event_bus),
        {"body": {"data": {"volume": 4}}},
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(VolumeEvent(volume=4, maximum=5))


def test_get_volume_missing_field_requests_analysis() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetVolume.handle(cast("EventBus", event_bus), {"body": {"data": {}}})

    assert result.state == HandlingState.ANALYSE_LOGGED
    event_bus.notify.assert_not_called()


async def test_set_volume_uses_write_apn() -> None:
    client_mock = AsyncMock(spec_set=NgiotClient)
    client_mock.request.return_value = {"body": {"code": 0, "msg": "ok"}}
    device_info = _api_device()

    response = await SetVolume(3)._request_ngiot(
        cast("NgiotClient", client_mock),
        device_info,
    )

    assert response == {"body": {"code": 0, "msg": "ok"}}
    client_mock.request.assert_awaited_once_with(
        device_info,
        NgiotRequest(apn=APN_SET_VOLUME, body_data={"volume": 3}),
    )


@pytest.mark.parametrize("volume", [-1, 6])
async def test_set_volume_rejects_out_of_range_values(volume: int) -> None:
    with pytest.raises(ValueError, match="Volume must be between"):
        await SetVolume(volume)._request_ngiot(
            cast("NgiotClient", AsyncMock(spec_set=NgiotClient)),
            _api_device(),
        )


def test_set_volume_notifies_event_after_success() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = SetVolume(2)._handle_response(
        cast("EventBus", event_bus),
        {"ret": "ok", "resp": {"body": {"code": 0, "msg": "ok"}}},
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(VolumeEvent(volume=2, maximum=5))
