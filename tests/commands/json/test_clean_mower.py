"""Tests regarding the clean commands of newer mowers."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from deebot_client.authentication import Authenticator
from deebot_client.commands.json import GetChargeInfo, GetScheduleTaskInfo
from deebot_client.commands.json.clean import (
    CleanAreaMower,
    CleanBorderMower,
    CleanMower,
    GetCleanInfoMower,
)
from deebot_client.event_bus import EventBus
from deebot_client.events import StateEvent
from deebot_client.events.mower import MowingTaskEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.messages.json import OnScheduleTaskInfo
from deebot_client.models import (
    ApiDeviceInfo,
    CleanAction,
    CleanMode,
    Credentials,
    State,
)
from tests.helpers import get_message_json, get_request_json, get_success_body
from tests.messages.json import assert_message

from . import assert_command

_DEVICE_CLASS = "2px96q"


def _clean_state(motion_state: str, content: dict[str, Any]) -> dict[str, Any]:
    return {
        "trigger": "app",
        "other": "",
        "state": "clean",
        "cleanState": {"motionState": motion_state, "cid": "122", "content": content},
    }


@pytest.mark.parametrize(
    ("command", "args"),
    [
        (CleanMower(CleanAction.START), {"act": "start", "content": {"type": "auto"}}),
        (CleanMower(CleanAction.PAUSE), {"act": "pause", "content": {"type": ""}}),
        (CleanMower(CleanAction.STOP), {"act": "stop", "content": {"type": ""}}),
        (
            CleanAreaMower(CleanMode.SPOT_AREA, [2]),
            {"act": "start", "content": {"type": "spotArea", "value": "2"}},
        ),
    ],
)
def test_CleanMower(command: CleanMower, args: dict[str, Any]) -> None:
    assert command.NAME == "clean"
    assert command._args == args


@pytest.mark.parametrize(
    ("action", "state", "task", "expected"),
    [
        (
            CleanAction.PAUSE,
            State.CLEANING,
            "auto",
            {"act": "pause", "content": {"type": "auto"}},
        ),
        (
            CleanAction.STOP,
            State.CLEANING,
            "border",
            {"act": "stop", "content": {"type": "border"}},
        ),
        (
            CleanAction.START,
            State.PAUSED,
            "spotArea",
            {"act": "resume", "content": {"type": "spotArea"}},
        ),
        (
            CleanAction.START,
            State.DOCKED,
            None,
            {"act": "start", "content": {"type": "auto"}},
        ),
        (
            CleanAction.PAUSE,
            State.CLEANING,
            None,
            {"act": "pause", "content": {"type": ""}},
        ),
    ],
)
async def test_CleanMower_task_type(
    action: CleanAction, state: State, task: str | None, expected: dict[str, Any]
) -> None:
    """Pause/resume/stop should contain the type of the current task."""
    await _assert_sent(
        CleanMower(action),
        state,
        MowingTaskEvent(type=task, area_ids=[]),
        "clean",
        expected,
    )


@pytest.mark.parametrize(
    ("command", "state", "expected_name", "expected"),
    [
        (
            CleanMower(CleanAction.PAUSE),
            State.CLEANING,
            "setScheduleTask",
            {"act": "pause"},
        ),
        (
            CleanMower(CleanAction.START),
            State.PAUSED,
            "setScheduleTask",
            {"act": "resume"},
        ),
        (
            CleanMower(CleanAction.RESUME),
            State.PAUSED,
            "setScheduleTask",
            {"act": "resume"},
        ),
        (
            CleanMower(CleanAction.STOP),
            State.CLEANING,
            "clean",
            {"act": "stop", "content": {"type": "spotArea"}},
        ),
        (
            CleanAreaMower(CleanMode.SPOT_AREA, [2]),
            State.PAUSED,
            "clean",
            {"act": "start", "content": {"type": "spotArea", "value": "2"}},
        ),
        (
            CleanBorderMower("1"),
            State.PAUSED,
            "clean",
            {"act": "start", "content": {"type": "border", "value": "aid:1"}},
        ),
        (
            CleanBorderMower(["2", "1"]),
            State.IDLE,
            "clean",
            {"act": "start", "content": {"type": "border", "value": "aid:2;aid:1"}},
        ),
        (
            CleanAreaMower(CleanMode.SPOT_AREA, [1, 2]),
            State.IDLE,
            "clean",
            {"act": "start", "content": {"type": "spotArea", "value": "1,2"}},
        ),
    ],
)
async def test_CleanMower_scheduled(
    command: CleanMower,
    state: State,
    expected_name: str,
    expected: dict[str, Any],
) -> None:
    """Scheduled tasks are paused/resumed with setScheduleTask; new tasks start always."""
    await _assert_sent(
        command,
        state,
        MowingTaskEvent(type="spotArea", area_ids=["1"], scheduled=True),
        expected_name,
        expected,
    )


async def _assert_sent(
    command: CleanMower,
    state: State,
    task: MowingTaskEvent,
    expected_name: str,
    expected: dict[str, Any],
) -> None:
    last_events = {StateEvent: StateEvent(state), MowingTaskEvent: task}
    json, _ = get_request_json(get_success_body())
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.side_effect = last_events.get
    authenticator = Mock(spec_set=Authenticator)
    authenticator.authenticate = AsyncMock(return_value=Credentials("t", "u", 0))
    authenticator.post_authenticated = AsyncMock(return_value=json)
    device_info = ApiDeviceInfo(
        {"did": "did", "resource": "res", "class": _DEVICE_CLASS}  # type: ignore[typeddict-item]
    )

    result = await command.execute(authenticator, device_info, event_bus)

    assert result.device_reached
    sent = authenticator.post_authenticated.call_args.args[1]
    assert sent["cmdName"] == expected_name
    assert sent["payload"]["body"]["data"] == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (
            _clean_state(
                "working", {"type": "spotArea", "value": "2", "subContent": {}}
            ),
            (
                StateEvent(State.CLEANING),
                MowingTaskEvent(type="spotArea", area_ids=["2"]),
            ),
        ),
        (
            _clean_state("pause", {"type": "border", "value": "aid:1"}),
            (
                StateEvent(State.PAUSED),
                MowingTaskEvent(type="border", area_ids=["1"]),
            ),
        ),
        (
            _clean_state("working", {"type": "auto", "subContent": {"type": "auto"}}),
            (StateEvent(State.CLEANING), MowingTaskEvent(type="auto", area_ids=[])),
        ),
    ],
)
async def test_GetCleanInfoMower(
    data: dict[str, Any], expected: tuple[StateEvent, MowingTaskEvent]
) -> None:
    json, firmware_event = get_request_json(get_success_body(data))
    await assert_command(
        GetCleanInfoMower(),
        json,
        (firmware_event, *expected),
        device_class=_DEVICE_CLASS,
    )


async def test_GetCleanInfoMower_idle_requests_schedule() -> None:
    json, firmware_event = get_request_json(
        get_success_body({"trigger": "workComplete", "other": "", "state": "idle"})
    )
    schedule_json, _ = get_request_json(
        get_success_body(
            {
                "trigger": "schedule",
                "other": "",
                "ssid": "0",
                "state": "clean",
                "cleanState": {
                    "motionState": "working",
                    "content": {"type": "spotArea", "value": "1"},
                },
            }
        )
    )
    await assert_command(
        GetCleanInfoMower(),
        (json, schedule_json),
        (
            firmware_event,
            firmware_event,
            StateEvent(State.CLEANING),
            MowingTaskEvent(type="spotArea", area_ids=["1"], scheduled=True),
        ),
        device_class=_DEVICE_CLASS,
        expected_raw_response=json,
        handling_result=HandlingResult(
            HandlingState.SUCCESS, {"check_schedule": True}, [GetScheduleTaskInfo()]
        ),
    )


async def test_GetScheduleTaskInfo_idle() -> None:
    json, firmware_event = get_request_json(
        get_success_body({"trigger": "workComplete", "other": "", "state": "idle"})
    )
    await assert_command(
        GetScheduleTaskInfo(),
        json,
        (
            firmware_event,
            StateEvent(State.IDLE),
            MowingTaskEvent(type=None, area_ids=[]),
        ),
        device_class=_DEVICE_CLASS,
    )


def test_onScheduleTaskInfo() -> None:
    data, firmware_event = get_message_json(
        {
            "data": {
                "trigger": "schedule",
                "other": "",
                "ssid": "0",
                "state": "clean",
                "cleanState": {
                    "motionState": "working",
                    "content": {
                        "type": "spotArea",
                        "value": "1",
                        "subContent": {"type": "spotArea"},
                    },
                },
            }
        }
    )
    assert_message(
        OnScheduleTaskInfo,
        data,
        (
            firmware_event,
            StateEvent(State.CLEANING),
            MowingTaskEvent(type="spotArea", area_ids=["1"], scheduled=True),
        ),
        device_class=_DEVICE_CLASS,
    )


def test_onScheduleTaskInfo_vacuum_no_task_event() -> None:
    """Devices without mower capability should not get the mowing task event."""
    data, firmware_event = get_message_json(
        {"data": _clean_state("working", {"type": "spotArea", "value": "1"})}
    )
    assert_message(
        OnScheduleTaskInfo, data, (firmware_event, StateEvent(State.CLEANING))
    )


@pytest.mark.parametrize(
    ("state", "expected"),
    [("goCharging", StateEvent(State.RETURNING)), ("idle", None)],
)
async def test_GetChargeInfo(state: str, expected: StateEvent | None) -> None:
    json, firmware_event = get_request_json(
        get_success_body({"cid": "122", "trigger": "app", "state": state, "other": "0"})
    )
    events = (firmware_event, expected) if expected else firmware_event
    await assert_command(GetChargeInfo(), json, events)
