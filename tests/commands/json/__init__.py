from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, call

import orjson
from testfixtures import LogCapture

from deebot_client.event_bus import EventBus
from deebot_client.events import FirmwareEvent
from deebot_client.message import HandlingResult, HandlingState
from tests.commands import assert_command as assert_command_base
from tests.helpers import get_message_json, get_request_json, get_success_body

if TYPE_CHECKING:
    from deebot_client.command import Command
    from deebot_client.commands.json.common import (
        ExecuteCommand,
        JsonSetCommand,
        NgiotJsonCommand,
        SetEnableCommand,
    )
    from deebot_client.events import EnableEvent, Event
    from deebot_client.models import ApiDeviceInfo

__all__ = [
    "assert_command",
    "assert_execute_command",
    "assert_ngiot_invalid_query_data",
    "assert_ngiot_query",
    "assert_ngiot_write_and_read_back",
    "assert_set_command",
    "assert_set_enable_command",
]


async def assert_command(
    command: Command,
    json_api_response: dict[str, Any] | tuple[dict[str, Any], ...],
    expected_events: Event | Sequence[Event] | None,
    *,
    device_class: str = "kr0277",
    handling_result: HandlingResult | None = None,
    expected_raw_response: dict[str, Any] | None = None,
) -> None:
    await assert_command_base(
        command,
        json_api_response,
        expected_events,
        device_class=device_class,
        handling_result=handling_result,
        expected_raw_response=expected_raw_response,
    )


async def assert_execute_command(
    command: ExecuteCommand, args: dict[str, Any] | list[Any] | None
) -> None:
    assert command.NAME != "invalid"
    assert command._args == args

    # success
    json, firmware_event = get_request_json(get_success_body())
    await assert_command(command, json, firmware_event)

    # failed
    with LogCapture() as log:
        body = {"code": 500, "msg": "fail"}
        json, firmware_event = get_request_json(body)
        await assert_command(
            command,
            json,
            firmware_event,
            handling_result=HandlingResult(HandlingState.FAILED),
        )

        log.check_present(
            (
                "deebot_client.commands.json.common",
                "WARNING",
                f'Command "{command.NAME}" was not successfully. body={body}',
            )
        )


async def assert_set_command(
    command: JsonSetCommand,
    args: dict[str, Any],
    expected_get_command_events: Event | Sequence[Event],
) -> None:
    await assert_execute_command(command, args)

    event_bus = Mock(spec_set=EventBus)

    # Failed to set
    json_data, firmware_event = get_message_json(
        {
            "code": 500,
            "msg": "fail",
        }
    )
    command.handle_mqtt_p2p(event_bus, orjson.dumps(json_data))
    event_bus.notify.assert_called_once_with(firmware_event)

    event_bus.reset_mock()
    # Success
    data, firmware_event = get_message_json(get_success_body())
    command.handle_mqtt_p2p(event_bus, orjson.dumps(data))
    if not isinstance(expected_get_command_events, Sequence):
        expected_events = [firmware_event, expected_get_command_events]
    else:
        expected_events = [firmware_event, *expected_get_command_events]

    event_bus.notify.assert_has_calls([call(x) for x in expected_events])
    assert event_bus.notify.call_count == len(expected_events)

    payload = orjson.dumps({"body": {"data": args}})
    mqtt_command = command.create_from_mqtt(payload)
    assert mqtt_command == command


async def assert_set_enable_command(
    command: SetEnableCommand,
    expected_get_command_event: type[EnableEvent],
    *,
    enabled: bool,
    field_name: str = "enable",
) -> None:
    args = {field_name: 1 if enabled else 0}
    await assert_set_command(command, args, expected_get_command_event(enabled))


async def assert_ngiot_query(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    command: NgiotJsonCommand,
    field: str,
    value: int | bool,
    event: Event,
    code: int | str,
) -> None:
    response = {
        "header": {"fwVer": "1.2.3"},
        "body": {"code": code, "data": {field: value}},
    }
    authenticator.post_ngiot.return_value = response

    result = await command.execute(authenticator, api_device_info, event_bus_mock)

    authenticator.post_ngiot.assert_awaited_once_with(
        api_device_info, "10001", {"fields": [field]}
    )
    authenticator.post_authenticated.assert_not_called()
    assert result.device_reached
    assert result.raw_response == response
    assert result.raw_response["body"]["code"] == code
    assert event_bus_mock.notify.call_args_list == [
        call(FirmwareEvent("1.2.3")),
        call(event),
    ]


async def assert_ngiot_invalid_query_data(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    command: NgiotJsonCommand,
    data: dict[str, Any],
) -> None:
    authenticator.post_ngiot.return_value = {"body": {"code": 0, "data": data}}

    result = await command.execute(authenticator, api_device_info, event_bus_mock)

    assert not result.device_reached
    event_bus_mock.notify.assert_not_called()


async def assert_ngiot_write_and_read_back(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    command: NgiotJsonCommand,
    apn: str,
    field: str,
    requested: int | bool,
    reported: int | bool,
    event: Event,
    code: int | str,
) -> None:
    ack = {"body": {"code": code, "msg": "ok"}}
    authenticator.post_ngiot.side_effect = [
        ack,
        {"body": {"code": 0, "data": {field: reported}}},
    ]

    result = await command.execute(authenticator, api_device_info, event_bus_mock)

    assert result.device_reached
    assert result.raw_response == ack
    assert result.raw_response["body"]["code"] == code
    assert authenticator.post_ngiot.await_args_list == [
        call(api_device_info, apn, {field: requested}),
        call(api_device_info, "10001", {"fields": [field]}),
    ]
    authenticator.post_authenticated.assert_not_called()
    event_bus_mock.notify.assert_called_once_with(event)
