from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.xml import GetCleanSpeed, SetCleanSpeed
from deebot_client.events import FanSpeedEvent, FanSpeedLevel
from deebot_client.message import HandlingState
from tests.commands import assert_command

from . import get_request_xml

if TYPE_CHECKING:
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("speed", "expected_event"),
    [
        ("standard", FanSpeedEvent(FanSpeedLevel.STANDARD)),
        ("strong", FanSpeedEvent(FanSpeedLevel.STRONG)),
    ],
    ids=["standard", "strong"],
)
async def test_get_fan_speed(speed: str, expected_event: Event) -> None:
    json = get_request_xml(f"<ctl ret='ok' speed='{speed}'/>")
    await assert_command(GetCleanSpeed(), json, expected_event)


@pytest.mark.parametrize(
    "xml",
    ["<ctl ret='error'/>", "<ctl ret='ok' speed='invalid'/>"],
    ids=["error", "no_state"],
)
async def test_get_fan_speed_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetCleanSpeed(),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )


async def test_set_fan_speed() -> None:
    command = SetCleanSpeed(FanSpeedLevel.STRONG)
    json = get_request_xml("<ctl ret='ok' />")
    await assert_command(command, json, None, command_result=CommandResult(HandlingState.SUCCESS))


async def test_set_fan_speed_error() -> None:
    command = SetCleanSpeed("invalid")
    json = get_request_xml("<ctl ret='error' />")
    await assert_command(command, json, None, command_result=CommandResult(HandlingState.FAILED))
