from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, Mock

from deebot_client.commands.ngiot.child_lock import GetChildLock, SetChildLock
from deebot_client.commands.ngiot.common import APN_CHILD_LOCK
from deebot_client.event_bus import EventBus
from deebot_client.events import ChildLockEvent
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


def test_get_child_lock_notifies_event() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetChildLock.handle(
        cast("EventBus", event_bus),
        {"body": {"data": {"childLock": True}}},
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(ChildLockEvent(enabled=True))


def test_get_child_lock_missing_field_requests_analysis() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetChildLock.handle(cast("EventBus", event_bus), {"body": {"data": {}}})

    assert result.state == HandlingState.ANALYSE_LOGGED
    event_bus.notify.assert_not_called()


async def test_set_child_lock_uses_write_apn() -> None:
    client_mock = AsyncMock(spec_set=NgiotClient)
    client_mock.request.return_value = {"body": {"code": 0, "msg": "ok"}}
    device_info = _api_device()

    response = await SetChildLock(True)._request_ngiot(
        cast("NgiotClient", client_mock),
        device_info,
    )

    assert response == {"body": {"code": 0, "msg": "ok"}}
    client_mock.request.assert_awaited_once_with(
        device_info,
        NgiotRequest(apn=APN_CHILD_LOCK, body_data={"childLock": True}),
    )


def test_set_child_lock_notifies_event_after_success() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = SetChildLock(False)._handle_response(
        cast("EventBus", event_bus),
        {"ret": "ok", "resp": {"body": {"code": 0, "msg": "ok"}}},
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(ChildLockEvent(enabled=False))
