from __future__ import annotations

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.xml import GetCleanState
from deebot_client.commands.xml.clean import CleanArea
from deebot_client.events import FanSpeedEvent, FanSpeedLevel, StateEvent
from deebot_client.message import HandlingState
from deebot_client.models import CleanMode, State
from tests.commands import assert_command

from . import get_request_xml


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
    ("speed", "state", "expected_fan_speed_event", "expected_state_event"),
    [
        (
            "standard",
            "s",
            FanSpeedEvent(FanSpeedLevel.NORMAL),
            StateEvent(State.CLEANING),
        ),
        (
            "strong",
            "s",
            FanSpeedEvent(FanSpeedLevel.MAX),
            StateEvent(State.CLEANING),
        ),
        (
            "standard",
            "p",
            FanSpeedEvent(FanSpeedLevel.NORMAL),
            StateEvent(State.PAUSED),
        ),
    ],
    ids=["standard_cleaning", "strong_cleaning", "paused"],
)
async def test_get_clean_state(
    speed: str,
    state: str,
    expected_fan_speed_event: FanSpeedEvent,
    expected_state_event: StateEvent,
) -> None:
    json = get_request_xml(
        f"<ctl ret='ok'><clean type='auto' speed='{speed}' st='{state}' t='0' a='0' s='0' tr=''/></ctl>"
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
