from collections.abc import Callable, Sequence
from typing import Any
from unittest.mock import AsyncMock, Mock, call

from deebot_client.authentication import Authenticator
from deebot_client.command import Command, CommandResult
from deebot_client.event_bus import EventBus
from deebot_client.events import Event
from deebot_client.models import Credentials, DeviceInfo, StaticDeviceInfo


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
    *,
    static_device_info: StaticDeviceInfo,
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
        static_device_info,
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
