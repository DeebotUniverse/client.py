from collections.abc import Sequence
from typing import Any
from unittest.mock import AsyncMock, Mock, call

from deebot_client import Authenticator
from deebot_client.command import Command
from deebot_client.commands import CommandWithHandling, SetCommand
from deebot_client.commands.common import CommandResult as CommandResultOld
from deebot_client.events import Event
from deebot_client.events.event_bus import EventBus
from deebot_client.models import Credentials, DeviceInfo
from tests.helpers import get_message_json


async def assert_command_requested(
    command: Command,
    json: dict[str, Any],
    expected_events: Event | None | Sequence[Event],
) -> None:
    event_bus = Mock(spec_set=EventBus)
    authenticator = Mock(spec_set=Authenticator)
    authenticator.authenticate = AsyncMock(
        return_value=Credentials("token", "user_id", 9999)
    )
    authenticator.post_authenticated = AsyncMock(return_value=json)
    device_info = DeviceInfo(
        {
            "company": "company",
            "did": "did",
            "name": "name",
            "nick": "nick",
            "resource": "resource",
            "deviceName": "device_name",
            "status": "status",
            "class": "get_class",
        }
    )

    await command.execute(authenticator, device_info, event_bus)

    # verify
    authenticator.post_authenticated.assert_called()
    if expected_events:
        if isinstance(expected_events, Sequence):
            event_bus.notify.assert_has_calls([call(x) for x in expected_events])
            assert event_bus.notify.call_count == len(expected_events)
        else:
            event_bus.notify.assert_called_once_with(expected_events)
    else:
        event_bus.notify.assert_not_called()


def assert_command_requestedOLD(
    command: CommandWithHandling,
    json: dict[str, Any],
    expected_events: Event | None | Sequence[Event],
    expected_result: CommandResultOld = CommandResultOld.success(),
) -> None:
    event_bus = Mock(spec_set=EventBus)

    assert command.name != "invalid"

    result = command.handle_requested(event_bus, json)

    assert result == expected_result
    if expected_events:
        if isinstance(expected_events, Sequence):
            event_bus.notify.assert_has_calls([call(x) for x in expected_events])
            assert event_bus.notify.call_count == len(expected_events)
        else:
            event_bus.notify.assert_called_once_with(expected_events)
    else:
        event_bus.notify.assert_not_called()


def assert_set_command(
    command: SetCommand,
    args: dict | list | None,
    expected_get_command_event: Event,
) -> None:
    assert command.name != "invalid"
    assert command.args == args

    event_bus = Mock(spec_set=EventBus)

    # Failed to set
    json = {
        "header": {
            "pri": 1,
            "tzm": 480,
            "ts": "1304623069888",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
        },
        "body": {
            "code": 500,
            "msg": "fail",
        },
    }
    command.handle_mqtt_p2p(event_bus, json)
    event_bus.notify.assert_not_called()

    # Success
    command.handle_mqtt_p2p(event_bus, get_message_json(None))
    event_bus.notify.assert_called_once_with(expected_get_command_event)
