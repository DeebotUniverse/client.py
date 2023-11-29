from collections.abc import Callable, Sequence
from typing import Any
from unittest.mock import AsyncMock, Mock, call

from testfixtures import LogCapture

from deebot_client.authentication import Authenticator
from deebot_client.command import Command, CommandResult
from deebot_client.commands.json.common import (
    ExecuteCommand,
    JsonSetCommand,
    SetEnableCommand,
)
from deebot_client.event_bus import EventBus
from deebot_client.events import EnableEvent, Event
from deebot_client.hardware.deebot import FALLBACK, get_static_device_info
from deebot_client.message import HandlingState
from deebot_client.models import Credentials, DeviceInfo
from tests.helpers import get_message_json, get_request_json, get_success_body


def _wrap_command(command: Command) -> tuple[Command, Callable[[CommandResult], None]]:
    result: CommandResult | None = None
    execute_fn = command._execute

    async def _execute(
        _: Command,
        authenticator: Authenticator,
        device_info: DeviceInfo,
        event_bus: EventBus,
    ) -> CommandResult:
        nonlocal result
        result = await execute_fn(authenticator, device_info, event_bus)
        return result

    def verify_result(expected_result: CommandResult) -> None:
        assert result == expected_result

    command._execute = _execute.__get__(command)  # type: ignore[method-assign]
    return (command, verify_result)


async def assert_command(
    command: Command,
    json_api_response: dict[str, Any],
    expected_events: Event | None | Sequence[Event],
    command_result: CommandResult | None = None,
) -> None:
    command_result = command_result or CommandResult.success()
    event_bus = Mock(spec_set=EventBus)
    authenticator = Mock(spec_set=Authenticator)
    authenticator.authenticate = AsyncMock(
        return_value=Credentials("token", "user_id", 9999)
    )
    authenticator.post_authenticated = AsyncMock(return_value=json_api_response)
    device_info = DeviceInfo(
        {
            "company": "company",
            "did": "did",
            "name": "name",
            "nick": "nick",
            "resource": "resource",
            "deviceName": "device_name",
            "status": 1,
            "class": "get_class",
        },
        get_static_device_info(FALLBACK),
    )

    command, verify_result = _wrap_command(command)

    await command.execute(authenticator, device_info, event_bus)

    # verify
    verify_result(command_result)
    authenticator.post_authenticated.assert_called()
    if expected_events:
        if isinstance(expected_events, Sequence):
            event_bus.notify.assert_has_calls([call(x) for x in expected_events])
            assert event_bus.notify.call_count == len(expected_events)
        else:
            event_bus.notify.assert_called_once_with(expected_events)
    else:
        event_bus.notify.assert_not_called()


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
        await assert_command(command, json, None, CommandResult(HandlingState.FAILED))

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
) -> None:
    args = {"enable": 1 if enabled else 0}
    await assert_set_command(command, args, expected_get_command_event(enabled))
