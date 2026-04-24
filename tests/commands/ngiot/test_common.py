from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from deebot_client.commands.ngiot.battery import GetBattery
from deebot_client.commands.ngiot.common import APN_ROBOT_DETAIL
from deebot_client.event_bus import EventBus
from deebot_client.events import AvailabilityEvent, BatteryEvent
from deebot_client.exceptions import ApiError
from deebot_client.ngiot_client import NgiotRequest


@pytest.fixture
def api_device() -> dict[str, Any]:
    return {
        "did": "did-1",
        "class": "eyfj07",
        "resource": "res-1",
        "service": {"mqs": "service.example.com"},
    }


@pytest.fixture
def event_bus() -> Mock:
    return Mock(spec_set=EventBus)


async def test_ngiot_get_command_uses_attached_client(
    api_device: dict[str, Any],
    event_bus: Mock,
) -> None:
    ngiot_client = AsyncMock()
    ngiot_client.request.return_value = {"body": {"code": 0, "data": {"battery": 88}}}
    authenticator = Mock(ngiot_client=ngiot_client)

    result = await GetBattery().execute(authenticator, api_device, event_bus)

    assert result.device_reached is True
    ngiot_client.request.assert_awaited_once_with(
        api_device,
        NgiotRequest(
            apn=APN_ROBOT_DETAIL,
            body_data={"fields": ["battery"]},
        ),
    )
    event_bus.notify.assert_any_call(AvailabilityEvent(available=True))
    event_bus.notify.assert_any_call(BatteryEvent(88))


async def test_ngiot_command_without_attached_client_fails(
    api_device: dict[str, Any],
    event_bus: Mock,
) -> None:
    authenticator = Mock(ngiot_client=None)

    result = await GetBattery().execute(authenticator, api_device, event_bus)

    assert result.device_reached is False
    event_bus.notify.assert_not_called()


async def test_get_ngiot_client_raises_without_attached_client(
    api_device: dict[str, Any],
) -> None:
    command = GetBattery()
    authenticator = Mock(ngiot_client=None)

    with pytest.raises(ApiError, match="NGIOT client is not attached"):
        await command._get_ngiot_client(authenticator, api_device)
