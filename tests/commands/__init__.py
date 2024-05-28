from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock, call

from deebot_client.authentication import Authenticator
from deebot_client.command import Command, CommandResult
from deebot_client.event_bus import EventBus
from deebot_client.models import (
    ApiDeviceInfo,
    Credentials,
)

if TYPE_CHECKING:
    from deebot_client.events import Event


def _wrap_command(
    command: Command,
) -> tuple[Command, Callable[[CommandResult, dict[str, Any] | None], None]]:
    result: CommandResult | None = None
    response: dict[str, Any] | None = None
    execute_fn = command._execute

    async def _execute(
        _: Command,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[CommandResult, dict[str, Any]]:
        nonlocal result, response
        result, response = await execute_fn(authenticator, device_info, event_bus)
        return result, response

    def verify_result(
        expected_result: CommandResult, expected_response: dict[str, Any] | None = None
    ) -> None:
        assert result == expected_result
        if expected_response is not None:
            assert response == expected_response

    command._execute = _execute.__get__(command)  # type: ignore[method-assign]
    return (command, verify_result)


async def assert_command(
    command: Command,
    json_api_response: dict[str, Any] | tuple[dict[str, Any], ...],
    expected_events: Event | None | Sequence[Event],
    *,
    command_result: CommandResult | None = None,
    expected_raw_response: dict[str, Any] | None = None,
) -> None:
    command_result = command_result or CommandResult.success()
    event_bus = Mock(spec_set=EventBus)
    authenticator = Mock(spec_set=Authenticator)
    authenticator.authenticate = AsyncMock(
        return_value=Credentials("token", "user_id", 9999)
    )
    if isinstance(json_api_response, tuple):
        authenticator.post_authenticated = AsyncMock(side_effect=json_api_response)
    else:
        authenticator.post_authenticated = AsyncMock(return_value=json_api_response)
        if expected_raw_response is None:
            expected_raw_response = json_api_response
    device_info = ApiDeviceInfo(
        {
            "company": "company",
            "did": "did",
            "name": "name",
            "nick": "nick",
            "resource": "resource",
            "class": "get_class",
        }
    )

    command, verify_result = _wrap_command(command)

    await command.execute(authenticator, device_info, event_bus)

    # verify
    verify_result(command_result, expected_raw_response)
    authenticator.post_authenticated.assert_called()
    if expected_events:
        if isinstance(expected_events, Sequence):
            event_bus.notify.assert_has_calls([call(x) for x in expected_events])
            assert event_bus.notify.call_count == len(expected_events)
        else:
            event_bus.notify.assert_called_once_with(expected_events)
    else:
        event_bus.notify.assert_not_called()
