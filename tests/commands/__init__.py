from collections.abc import Sequence
from typing import Any
from unittest.mock import AsyncMock, Mock, call

from deebot_client.authentication import Authenticator
from deebot_client.command import Command
from deebot_client.commands import SetCommand
from deebot_client.events import Event
from deebot_client.events.event_bus import EventBus
from deebot_client.models import Credentials, DeviceInfo

from ..helpers import get_message_json, get_request_json


async def assert_command(
    command: Command,
    json_api_response: dict[str, Any],
    expected_events: Event | None | Sequence[Event],
) -> None:
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


async def assert_set_command(
    command: SetCommand,
    args: dict | list | None,
    expected_get_command_event: Event,
) -> None:
    assert command.name != "invalid"
    assert command._args == args

    json = get_request_json({"code": 0, "msg": "ok"})
    await assert_command(command, json, None)

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
