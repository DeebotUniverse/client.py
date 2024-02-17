from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.json import Clean, GetCleanInfo, GetCleanInfoV2
from deebot_client.event_bus import EventBus
from deebot_client.events import StateEvent
from deebot_client.message import HandlingState
from deebot_client.models import CleanAction, DeviceInfo, State
from tests.helpers import get_request_json, get_success_body

from . import assert_command

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator


@pytest.mark.parametrize(
    ("data", "expected_event", "expected_state"),
    [
        ({"trigger": "none"}, None, HandlingState.ANALYSE_LOGGED),
        ({"trigger": "alert"}, StateEvent(State.ERROR), HandlingState.SUCCESS),
        (
            {"trigger": "none", "state": "idle"},
            StateEvent(State.IDLE),
            HandlingState.SUCCESS,
        ),
        (
            {"trigger": "none", "state": "goCharging"},
            StateEvent(State.RETURNING),
            HandlingState.SUCCESS,
        ),
        (
            {
                "trigger": "none",
                "state": "clean",
                "cleanState": {"motionState": "working"},
            },
            StateEvent(State.CLEANING),
            HandlingState.SUCCESS,
        ),
        (
            {
                "trigger": "none",
                "state": "clean",
                "cleanState": {"motionState": "pause"},
            },
            StateEvent(State.PAUSED),
            HandlingState.SUCCESS,
        ),
        (
            {
                "trigger": "none",
                "state": "clean",
                "cleanState": {"motionState": "goCharging"},
            },
            StateEvent(State.RETURNING),
            HandlingState.SUCCESS,
        ),
        (
            {
                "trigger": "app",
                "state": "clean",
                "cleanState": {
                    "id": "122",
                    "router": "plan",
                    "type": "customArea",
                    "content": "639.000000,166.000000,1711.000000,-705.000000",
                    "count": 1,
                    "motionState": "working",
                },
            },
            StateEvent(State.CLEANING),
            HandlingState.SUCCESS,
        ),
        (
            {
                "trigger": "app",
                "state": "clean",
                "cleanState": {
                    "id": "122",
                    "router": "plan",
                    "type": "customArea",
                    "content": {
                        "value": "639.000000,166.000000,1711.000000,-705.000000"
                    },
                    "count": 1,
                    "motionState": "working",
                },
            },
            StateEvent(State.CLEANING),
            HandlingState.SUCCESS,
        ),
    ],
)
async def test_GetCleanInfo(
    data: dict[str, Any],
    expected_event: StateEvent,
    expected_state: HandlingState,
) -> None:
    json = get_request_json(get_success_body(data))
    await assert_command(
        GetCleanInfo(),
        json,
        expected_event,
        command_result=CommandResult(expected_state),
    )
    await assert_command(
        GetCleanInfoV2(),
        json,
        expected_event,
        command_result=CommandResult(expected_state),
    )


@pytest.mark.parametrize(
    ("action", "state", "expected"),
    [
        (CleanAction.START, None, CleanAction.START),
        (CleanAction.START, State.PAUSED, CleanAction.RESUME),
        (CleanAction.START, State.DOCKED, CleanAction.START),
        (CleanAction.RESUME, None, CleanAction.RESUME),
        (CleanAction.RESUME, State.PAUSED, CleanAction.RESUME),
        (CleanAction.RESUME, State.DOCKED, CleanAction.START),
    ],
)
async def test_Clean_act(
    authenticator: Authenticator,
    device_info: DeviceInfo,
    action: CleanAction,
    state: State | None,
    expected: CleanAction,
) -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.return_value = (
        StateEvent(state) if state is not None else None
    )
    command = Clean(action)

    await command.execute(authenticator, device_info, event_bus)

    assert isinstance(command._args, dict)
    assert command._args["act"] == expected.value
