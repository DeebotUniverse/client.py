from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from deebot_client.commands.json import GetCleanInfo
from deebot_client.commands.json.clean import Clean, CleanV2, GetCleanInfoV2
from deebot_client.event_bus import EventBus
from deebot_client.events import StateEvent
from deebot_client.models import ApiDeviceInfo, CleanAction, State
from tests.helpers import get_request_json, get_success_body

from . import assert_command

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator


@pytest.mark.parametrize("command", [GetCleanInfo(), GetCleanInfoV2()])
@pytest.mark.parametrize(
    ("json", "expected"),
    [
        (
            get_request_json(get_success_body({"trigger": "none", "state": "idle"})),
            StateEvent(State.IDLE),
        ),
    ],
)
async def test_GetCleanInfo(
    command: GetCleanInfo, json: dict[str, Any], expected: StateEvent
) -> None:
    await assert_command(command, json, expected)


@pytest.mark.parametrize("command_type", [Clean, CleanV2])
@pytest.mark.parametrize(
    ("action", "state", "expected"),
    [
        (CleanAction.START, None, CleanAction.START),
        (CleanAction.START, State.PAUSED, CleanAction.RESUME),
        (CleanAction.START, State.DOCKED, CleanAction.START),
        (CleanAction.RESUME, None, CleanAction.RESUME),
        (CleanAction.RESUME, State.PAUSED, CleanAction.RESUME),
        (CleanAction.RESUME, State.DOCKED, CleanAction.START),
        (CleanAction.STOP, None, CleanAction.STOP),
        (CleanAction.STOP, State.CLEANING, CleanAction.STOP),
        (CleanAction.STOP, State.PAUSED, CleanAction.STOP),
        (CleanAction.STOP, State.DOCKED, CleanAction.STOP),
    ],
)
async def test_Clean_act(
    authenticator: Authenticator,
    api_device_info: ApiDeviceInfo,
    command_type: type[Clean],
    action: CleanAction,
    state: State | None,
    expected: CleanAction,
) -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.return_value = (
        StateEvent(state) if state is not None else None
    )
    command = command_type(action)

    await command.execute(authenticator, api_device_info, event_bus)

    assert isinstance(command._args, dict)
    assert command._args["act"] == expected.value

    if command_type is CleanV2:
        assert isinstance(command._args["content"], dict)
