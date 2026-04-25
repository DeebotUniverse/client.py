from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, Mock

from deebot_client.commands.ngiot.common import APN_RESET_CONSUMABLE
from deebot_client.commands.ngiot.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.event_bus import EventBus
from deebot_client.events import LifeSpan, LifeSpanEvent
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


def test_get_life_span_notifies_supported_consumables() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetLifeSpan.handle(
        cast(EventBus, event_bus),
        {
            "body": {
                "data": {
                    "consumables": [
                        {"type": "rollBrush", "left": 60, "total": 120},
                        {"type": "filter", "left": 45, "total": 90},
                        {"type": "unknown", "left": 1, "total": 2},
                    ]
                }
            }
        },
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_any_call(LifeSpanEvent(LifeSpan.BRUSH, 50.0, 60))
    event_bus.notify.assert_any_call(LifeSpanEvent(LifeSpan.FILTER, 50.0, 45))
    assert event_bus.notify.call_count == 2


async def test_reset_life_span_uses_reset_consumable_apn() -> None:
    client_mock = AsyncMock(spec_set=NgiotClient)
    client_mock.request.return_value = {"body": {"code": 0, "msg": "ok"}}
    device_info = _api_device()

    response = await ResetLifeSpan("FILTER")._request_ngiot(
        cast(NgiotClient, client_mock),
        device_info,
    )

    assert response == {"body": {"code": 0, "msg": "ok"}}
    client_mock.request.assert_awaited_once_with(
        device_info,
        NgiotRequest(
            apn=APN_RESET_CONSUMABLE,
            body_data={"resetConsumable": "filter"},
        ),
    )


def test_reset_life_span_requests_refresh_after_success() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = ResetLifeSpan("SIDE_BRUSH")._handle_response(
        cast(EventBus, event_bus),
        {"ret": "ok", "resp": {"body": {"code": 0, "msg": "ok"}}},
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.request_refresh.assert_called_once_with(LifeSpanEvent)