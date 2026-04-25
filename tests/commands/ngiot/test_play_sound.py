from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock

from deebot_client.commands.ngiot.common import APN_DEVICE_LOCATE
from deebot_client.commands.ngiot.play_sound import PlaySound
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


async def test_play_sound_uses_locate_apn() -> None:
    client_mock = AsyncMock(spec_set=NgiotClient)
    client_mock.request.return_value = {"body": {"code": 0, "msg": "ok"}}
    device_info = _api_device()

    response = await PlaySound()._request_ngiot(
        cast(NgiotClient, client_mock),
        device_info,
    )

    assert response == {"body": {"code": 0, "msg": "ok"}}
    client_mock.request.assert_awaited_once_with(
        device_info,
        NgiotRequest(apn=APN_DEVICE_LOCATE, body_data={"seek": True}),
    )