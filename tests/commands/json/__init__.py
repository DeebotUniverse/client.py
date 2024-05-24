from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

from testfixtures import LogCapture

from deebot_client.command import CommandResult
from deebot_client.event_bus import EventBus
from deebot_client.message import HandlingState
from tests.commands import assert_command, assert_command_response
from tests.helpers import get_message_json, get_request_json, get_success_body

if TYPE_CHECKING:
    from deebot_client.commands.json.common import (
        ExecuteCommand,
        JsonSetCommand,
        SetEnableCommand,
    )
    from deebot_client.events import EnableEvent, Event

__all__ = [
    "assert_command",
    "assert_command_response",
    "assert_execute_command",
    "assert_set_command",
    "assert_set_enable_command",
]


async def assert_execute_command(
    command: ExecuteCommand, args: dict[str, Any] | list[Any] | None
) -> None:
    assert command.name != "invalid"
    assert command._args == args

    # success
    json = get_request_json(get_success_body())
    await assert_command(command, json, None)

    # failed
    with LogCapture() as log:
        body = {"code": 500, "msg": "fail"}
        json = get_request_json(body)
        await assert_command(
            command, json, None, command_result=CommandResult(HandlingState.FAILED)
        )

        log.check_present(
            (
                "deebot_client.commands.json.common",
                "WARNING",
                f'Command "{command.name}" was not successfully. body={body}',
            )
        )


async def assert_set_command(
    command: JsonSetCommand,
    args: dict[str, Any],
    expected_get_command_event: Event,
) -> None:
    await assert_execute_command(command, args)

    event_bus = Mock(spec_set=EventBus)

    # Failed to set
    json = get_message_json(
        {
            "code": 500,
            "msg": "fail",
        }
    )
    command.handle_mqtt_p2p(event_bus, json)
    event_bus.notify.assert_not_called()

    # Success
    command.handle_mqtt_p2p(event_bus, get_message_json(get_success_body()))
    event_bus.notify.assert_called_once_with(expected_get_command_event)

    mqtt_command = command.create_from_mqtt(args)
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
