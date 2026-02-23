from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.commands.xml import Clean, CleanArea, GetCleanState
from deebot_client.events import FanSpeedEvent, FanSpeedLevel, StateEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import CleanAction, CleanMode, State

from . import assert_command, get_request_xml

if TYPE_CHECKING:
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    "command",
    [
        Clean(CleanAction.START, speed=FanSpeedLevel.MAX),
        Clean(CleanAction.PAUSE),
    ],
)
async def test_Clean(command: Clean) -> None:
    json = get_request_xml("<ctl ret='ok'/>")
    await assert_command(
        command, json, None, handling_result=HandlingResult(HandlingState.SUCCESS)
    )


@pytest.mark.parametrize(
    "command",
    [
        CleanArea(CleanMode.SPOT_AREA, [4], 1),
        CleanArea(CleanMode.CUSTOM_AREA, [1580.0, -4087.0, 3833.0, -7525.0]),
    ],
)
async def test_CleanArea(command: CleanArea) -> None:
    json = get_request_xml("<ctl ret='ok'/>")
    await assert_command(
        command, json, None, handling_result=HandlingResult(HandlingState.SUCCESS)
    )


@pytest.mark.parametrize(
    ("params", "expected_events"),
    [
        (
            "speed='standard' st='s'",
            [FanSpeedEvent(FanSpeedLevel.NORMAL), StateEvent(State.CLEANING)],
        ),
        (
            "speed='strong' st='s'",
            [FanSpeedEvent(FanSpeedLevel.MAX), StateEvent(State.CLEANING)],
        ),
        (
            "speed='standard' st='p'",
            [FanSpeedEvent(FanSpeedLevel.NORMAL), StateEvent(State.PAUSED)],
        ),
        (
            "st='r'",
            [StateEvent(State.CLEANING)],
        ),
        (
            "st='h'",
            [StateEvent(State.IDLE)],
        ),
        (
            "speed='strong'",
            [FanSpeedEvent(FanSpeedLevel.MAX)],
        ),
    ],
    ids=[
        "standard_cleaning",
        "strong_cleaning",
        "paused",
        "resume/cleaning",
        "stop/idle",
        "fanspeed_only",
    ],
)
async def test_get_clean_state(
    params: str,
    expected_events: list[Event],
) -> None:
    json = get_request_xml(
        f"<ctl ret='ok'><clean type='auto' {params} t='0' a='0' s='0' tr=''/></ctl>"
    )
    await assert_command(
        GetCleanState(),
        json,
        expected_events,
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
        handling_result=HandlingResult(HandlingState.ANALYSE_LOGGED),
    )
