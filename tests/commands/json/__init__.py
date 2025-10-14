from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, call

import orjson
from testfixtures import LogCapture

from deebot_client.event_bus import EventBus
from deebot_client.message import HandlingResult, HandlingState
from tests.commands import assert_command as assert_command_base
from tests.helpers import get_message_json, get_request_json, get_success_body

if TYPE_CHECKING:
    from deebot_client.command import Command
    from deebot_client.commands.json.common import (
        ExecuteCommand,
        JsonSetCommand,
        SetEnableCommand,
    )
    from deebot_client.events import EnableEvent, Event

__all__ = [
    "assert_command",
    "assert_execute_command",
    "assert_set_command",
    "assert_set_enable_command",
]


async def assert_command(
    command: Command,
    json_api_response: dict[str, Any] | tuple[dict[str, Any], ...],
    expected_events: Event | None | Sequence[Event],
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
