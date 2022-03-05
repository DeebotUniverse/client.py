from typing import Any, Optional, Union
from unittest.mock import Mock

from deebot_client.commands import CommandWithHandling, SetCommand
from deebot_client.events import Event
from deebot_client.events.event_bus import EventBus
from deebot_client.message import HandlingState
from tests.helpers import get_message_json


def assert_command_requested(
    command: CommandWithHandling, json: dict[str, Any], expected_event: Optional[Event]
) -> None:
    event_bus = Mock(spec_set=EventBus)

    assert command.name != "invalid"

    result = command.handle_requested(event_bus, json)

    assert result.state == HandlingState.SUCCESS
    if expected_event:
        event_bus.notify.assert_called_once_with(expected_event)
    else:
        event_bus.notify.assert_not_called()


def assert_set_command(
    command: SetCommand,
    args: Union[dict, list, None],
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
