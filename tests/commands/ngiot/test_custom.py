from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

from deebot_client.commands.ngiot.custom import CustomCommand
from deebot_client.event_bus import EventBus
from deebot_client.events import CustomCommandEvent
from deebot_client.message import HandlingState
from deebot_client.ngiot_client import NgiotRequest


async def test_custom_command_dispatches_explicit_ngiot_request() -> None:
    client = AsyncMock()
    client.request.return_value = {"body": {"code": 0, "data": {"ok": True}}}
    device_info: dict[str, Any] = {
        "did": "did-1",
        "class": "eyfj07",
        "resource": "res-1",
    }

    response = await CustomCommand(
        "12345",
        {"field": "value"},
        fmt="j",
        ct="q",
    )._request_ngiot(client, device_info)

    assert response == {"body": {"code": 0, "data": {"ok": True}}}
    client.request.assert_awaited_once_with(
        device_info,
        NgiotRequest(
            apn="12345",
            body_data={"field": "value"},
            fmt="j",
            ct="q",
        ),
    )


def test_custom_command_notifies_custom_command_event() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = CustomCommand("12345", {"field": "value"})._handle_response(
        event_bus,
        {"ret": "ok", "resp": {"body": {"code": 0, "data": {"ok": True}}}},
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(
        CustomCommandEvent(name="12345", response={"code": 0, "data": {"ok": True}})
    )
