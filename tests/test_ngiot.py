from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiohttp import ClientTimeout
import pytest

from deebot_client.commands.json.common import (
    ExecuteCommand,
    JsonGetCommand,
    NgiotJsonCommand,
)
from deebot_client.events import CustomCommandEvent, FirmwareEvent
from deebot_client.exceptions import ApiError, ApiTimeoutError, AuthenticationError
from deebot_client.message import HandlingResult

if TYPE_CHECKING:
    from unittest.mock import Mock

    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo


# Synthetic commands exercise the shared infrastructure without enabling a device.
class _Query(NgiotJsonCommand, JsonGetCommand):
    NAME = "testQuery"
    APN = "90001"

    def __init__(self) -> None:
        super().__init__({"fields": ["testField"]})

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        event_bus.notify(CustomCommandEvent(cls.NAME, data))
        return HandlingResult.success()


class _Control(NgiotJsonCommand, ExecuteCommand):
    NAME = "testControl"
    APN = "90002"

    def __init__(self) -> None:
        super().__init__({"testSwitch": True})


def test_missing_apn() -> None:
    with pytest.raises(ValueError, match="must have a APN attribute"):

        class MissingApn(NgiotJsonCommand, ExecuteCommand):
            NAME = "missingApn"


@pytest.mark.parametrize("code", [0, "0"])
async def test_query(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    code: int | str,
) -> None:
    data = {"testField": 42}
    response = {
        "header": {"fwVer": "1.2.3"},
        "body": {"code": code, "data": data},
    }
    authenticator.post_ngiot.return_value = response

    result = await _Query().execute(authenticator, api_device_info, event_bus_mock)

    authenticator.post_ngiot.assert_awaited_once_with(
        api_device_info, "90001", {"fields": ["testField"]}
    )
    authenticator.post_authenticated.assert_not_called()
    assert result.device_reached
    assert result.raw_response == response
    assert result.raw_response["body"]["code"] == code
    assert event_bus_mock.notify.call_count == 2
    event_bus_mock.notify.assert_any_call(FirmwareEvent("1.2.3"))
    event_bus_mock.notify.assert_any_call(CustomCommandEvent(_Query.NAME, data))


@pytest.mark.parametrize("code", [0, "0"])
async def test_control_ack(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    code: int | str,
) -> None:
    response = {"body": {"code": code, "msg": "ok"}}
    authenticator.post_ngiot.return_value = response

    result = await _Control().execute(authenticator, api_device_info, event_bus_mock)

    authenticator.post_ngiot.assert_awaited_once_with(
        api_device_info, "90002", {"testSwitch": True}
    )
    authenticator.post_authenticated.assert_not_called()
    assert result.device_reached
    assert result.raw_response == response
    assert result.raw_response["body"]["code"] == code
    event_bus_mock.notify.assert_not_called()


@pytest.mark.parametrize("command", [_Query(), _Control()])
@pytest.mark.parametrize("code", [1, "1"])
async def test_rejected_response(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    command: NgiotJsonCommand,
    code: int | str,
) -> None:
    authenticator.post_ngiot.return_value = {
        "body": {"code": code, "data": {"testField": 42}},
    }

    result = await command.execute(authenticator, api_device_info, event_bus_mock)

    assert not result.device_reached
    event_bus_mock.notify.assert_not_called()
    authenticator.post_ngiot.assert_awaited_once()


@pytest.mark.parametrize("body", [{"code": 0}, {"code": 0, "data": []}])
async def test_query_without_data(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    body: dict[str, Any],
) -> None:
    authenticator.post_ngiot.return_value = {"body": body}

    result = await _Query().execute(authenticator, api_device_info, event_bus_mock)

    assert not result.device_reached
    event_bus_mock.notify.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        ApiError("request failed"),
        AuthenticationError("unauthorized"),
        ApiTimeoutError("test", ClientTimeout(60)),
    ],
)
async def test_transport_failure(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    error: Exception,
) -> None:
    authenticator.post_ngiot.side_effect = error

    result = await _Control().execute(authenticator, api_device_info, event_bus_mock)

    assert not result.device_reached
    authenticator.post_ngiot.assert_awaited_once()
    authenticator.post_authenticated.assert_not_called()
    event_bus_mock.notify.assert_not_called()
