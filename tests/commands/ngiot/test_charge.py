from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, Mock

from deebot_client.commands.ngiot.charge import Charge
from deebot_client.commands.ngiot.common import APN_RETURN_TO_DOCK
from deebot_client.event_bus import EventBus
from deebot_client.events import StateEvent
from deebot_client.message import HandlingState
from deebot_client.models import ApiDeviceInfo, State
from deebot_client.ngiot_client import NgiotClient, NgiotRequest


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


def test_charge_handles_success_response() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = Charge.handle(event_bus, {"body": {"code": 0, "msg": "ok"}})

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(StateEvent(State.RETURNING))


async def test_charge_request_uses_return_to_dock_apn() -> None:
    client = AsyncMock(spec_set=NgiotClient)
    client.request.return_value = {"body": {"code": 0, "msg": "ok"}}
    device_info = _api_device()

    response = await Charge()._request_ngiot(client, device_info)

    assert response == {"body": {"code": 0, "msg": "ok"}}
    client.request.assert_awaited_once_with(
        device_info,
        NgiotRequest(
            apn=APN_RETURN_TO_DOCK,
            body_data={"chargeSwitch": True},
        ),
    )
