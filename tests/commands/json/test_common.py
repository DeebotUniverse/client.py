from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

from aiohttp import ClientTimeout
import pytest

from deebot_client.commands.json import (
    COMMANDS,
    GetBattery,
    GetChildLock,
    GetVolume,
    SetChildLock,
    SetVolume,
)
from deebot_client.commands.json.battery import NgiotGetBattery
from deebot_client.commands.json.child_lock import NgiotGetChildLock, NgiotSetChildLock
from deebot_client.commands.json.common import ExecuteCommand, NgiotJsonCommand
from deebot_client.commands.json.map import GetCachedMapInfo
from deebot_client.commands.json.volume import NgiotGetVolume, NgiotSetVolume
from deebot_client.event_bus import EventBus
from deebot_client.events import AvailabilityEvent
from deebot_client.exceptions import ApiError, ApiTimeoutError, AuthenticationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from deebot_client.command import CommandWithMessageHandling
    from deebot_client.models import ApiDeviceInfo

_ERROR_500 = {"ret": "fail", "errno": 500, "debug": "wait for response timed out"}
_ERROR_4200 = {
    "ret": "fail",
    "errno": 4200,
    "error": "endpoint offline",
    "debug": "jmq.clusterNode.FetchClientInfo rsp==null; no clientinfo in redis which means no ping was received from endpoint for a long time",
}


def _assert_false_and_not_called(event_bus: Mock) -> None:
    event_bus.assert_not_called()


def _assert_false_and_available_event_false(event_bus: Mock) -> None:
    event_bus.notify.assert_called_with(AvailabilityEvent(available=False))


@pytest.mark.parametrize(
    ("response_json", "expected_log", "assert_func"),
    [
        (
            _ERROR_500,
            (
                logging.WARNING,
                'No response received for command "{}". This can happen if the device has network issues or does not support the command',
            ),
            _assert_false_and_not_called,
        ),
        (
            {"ret": "fail", "errno": 123, "debug": "other error"},
            (
                logging.WARNING,
                'Command "{}" was not successfully.',
            ),
            _assert_false_and_not_called,
        ),
        (
            _ERROR_4200,
            (
                logging.INFO,
                'Device is offline. Could not execute command "{}"',
            ),
            _assert_false_and_available_event_false,
        ),
    ],
)
@pytest.mark.parametrize(
    "command", [GetBattery(), GetBattery(is_available_check=True), GetCachedMapInfo()]
)
async def test_common_functionality(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    command: CommandWithMessageHandling,
    response_json: dict[str, Any],
    expected_log: tuple[int, str],
    assert_func: Callable[[Mock], None],
    caplog: pytest.LogCaptureFixture,
) -> None:
    authenticator.post_authenticated.return_value = response_json
    event_bus = Mock(spec_set=EventBus)

    available = await command.execute(authenticator, api_device_info, event_bus)

    if response_json.get("errno") == 500 and command._is_available_check:
        assert (
            "deebot_client.command",
            logging.INFO,
            f'No response received for command "{command.NAME}" during availability-check.',
        ) in caplog.record_tuples

    elif expected_log:
        assert (
            "deebot_client.command",
            expected_log[0],
            expected_log[1].format(command.NAME),
        ) in caplog.record_tuples

    assert available.device_reached is False
    assert_func(event_bus)


def test_ngiot_missing_apn() -> None:
    with pytest.raises(ValueError, match="must have a APN attribute"):

        class MissingApn(NgiotJsonCommand, ExecuteCommand):
            """Invalid concrete command."""

            NAME = "missingApn"


@pytest.mark.parametrize(
    "command", [NgiotGetBattery(), NgiotSetVolume(2), NgiotSetChildLock(True)]
)
@pytest.mark.parametrize("code", [1, "1"])
async def test_ngiot_rejected_response(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    command: NgiotJsonCommand,
    code: int | str,
) -> None:
    authenticator.post_ngiot.return_value = {
        "body": {"code": code, "data": {"battery": 42}}
    }

    result = await command.execute(authenticator, api_device_info, event_bus_mock)

    assert not result.device_reached
    authenticator.post_ngiot.assert_awaited_once()
    event_bus_mock.notify.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        ApiError("request failed"),
        AuthenticationError("unauthorized"),
        ApiTimeoutError("test", ClientTimeout(60)),
    ],
)
async def test_ngiot_transport_error(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    error: Exception,
) -> None:
    authenticator.post_ngiot.side_effect = error

    result = await NgiotGetBattery().execute(
        authenticator, api_device_info, event_bus_mock
    )

    assert not result.device_reached
    authenticator.post_ngiot.assert_awaited_once()
    authenticator.post_authenticated.assert_not_called()
    event_bus_mock.notify.assert_not_called()


def test_ngiot_legacy_registry_unchanged() -> None:
    for legacy, ngiot in (
        (GetBattery, NgiotGetBattery),
        (GetVolume, NgiotGetVolume),
        (SetVolume, NgiotSetVolume),
        (GetChildLock, NgiotGetChildLock),
        (SetChildLock, NgiotSetChildLock),
    ):
        assert COMMANDS[legacy.NAME] is legacy
        assert ngiot.NAME not in COMMANDS
