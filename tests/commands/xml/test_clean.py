from __future__ import annotations

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.xml import Clean, CleanArea, GetCleanState
from deebot_client.events import FanSpeedEvent, FanSpeedLevel, StateEvent
from deebot_client.message import HandlingState
from deebot_client.models import CleanAction, CleanMode, State
from tests.commands import assert_command

from . import get_request_xml


@pytest.mark.parametrize(
    ("command", "command_result"),
    [
        (Clean(CleanAction.START, speed=FanSpeedLevel.MAX), HandlingState.SUCCESS),
        (Clean(CleanAction.PAUSE), HandlingState.SUCCESS),
    ],
)
async def test_Clean(command: Clean, command_result: HandlingState) -> None:
    json = get_request_xml("<ctl ret='ok'/>")
    await assert_command(
        command, json, None, command_result=CommandResult(command_result)
    )


@pytest.mark.parametrize(
    ("command", "command_result"),
    [
        (CleanArea(CleanMode.SPOT_AREA, "4", 1), HandlingState.SUCCESS),
    ],
)
async def test_CleanArea(command: CleanArea, command_result: HandlingState) -> None:
    json = get_request_xml("<ctl ret='ok'/>")
    await assert_command(
        command, json, None, command_result=CommandResult(command_result)
    )


@pytest.mark.parametrize(
    ("speed", "action", "expected_fan_speed_event", "expected_state_event"),
    [
        (
            FanSpeedLevel.NORMAL,
            CleanAction.START,
            FanSpeedEvent(FanSpeedLevel.NORMAL),
            StateEvent(State.CLEANING),
        ),
        (
            FanSpeedLevel.MAX,
            CleanAction.START,
            FanSpeedEvent(FanSpeedLevel.MAX),
            StateEvent(State.CLEANING),
        ),
        (
            FanSpeedLevel.NORMAL,
            CleanAction.PAUSE,
            FanSpeedEvent(FanSpeedLevel.NORMAL),
            StateEvent(State.PAUSED),
        ),
        (
            None,
            CleanAction.RESUME,
            None,
            StateEvent(State.IDLE),
        ),
        (
            None,
            CleanAction.STOP,
            None,
            StateEvent(State.IDLE),
        ),
        (
            FanSpeedLevel.MAX,
            None,
            FanSpeedEvent(FanSpeedLevel.MAX),
            None,
        ),
    ],
    ids=[
        "standard_cleaning",
        "strong_cleaning",
        "paused",
        "resume/idle",
        "stop/idle",
        "fanspeed_only",
    ],
)
async def test_get_clean_state(
    speed: FanSpeedLevel | None,
    action: CleanAction | None,
    expected_fan_speed_event: FanSpeedEvent,
    expected_state_event: StateEvent,
) -> None:
    speed_section = f"speed='{speed.xml_value}'" if speed is not None else ""
    state_section = f"st='{action.xml_value}'" if action is not None else ""
    json = get_request_xml(
        f"<ctl ret='ok'><clean type='auto' {speed_section} {state_section} t='0' a='0' s='0' tr=''/></ctl>"
    )
    await assert_command(
        GetCleanState(),
        json,
        [x for x in [expected_fan_speed_event, expected_state_event] if x is not None],
    )


@pytest.mark.parametrize(
    "xml",
    ["<ctl ret='error'/>", "<ctl ret='ok'></ctl>"],
    ids=["error", "no_state"],
)
async def test_get_clean_state_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetCleanState(),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )
