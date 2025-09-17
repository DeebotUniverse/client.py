from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.command import CommandResult, CommandWithMessageHandling
from deebot_client.commands.xml import GetCleanSpeed, SetCleanSpeed
from deebot_client.events import FanSpeedEvent, FanSpeedLevel
from deebot_client.message import HandlingState

from . import assert_command, get_request_xml

if TYPE_CHECKING:
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    "speed", list(FanSpeedLevel) + [level.name for level in FanSpeedLevel]
)
def test_GetCleanSpeed_should_build_with_string_and_enums(
    speed: str | FanSpeedLevel,
) -> None:
    """Test case for the way HA invokes the constructor."""
    assert SetCleanSpeed(speed) is not None


@pytest.mark.parametrize(
    ("speed", "expected_event"),
    [
        ("standard", FanSpeedEvent(FanSpeedLevel.NORMAL)),
        ("strong", FanSpeedEvent(FanSpeedLevel.MAX)),
    ],
    ids=["standard", "strong"],
)
async def test_get_fan_speed(speed: str, expected_event: Event) -> None:
    json = get_request_xml(f"<ctl ret='ok' speed='{speed}'/>")
    await assert_command(GetCleanSpeed(), json, expected_event)


@pytest.mark.parametrize(
    ("xml", "expected_state"),
    [
        ("<ctl ret='error'/>", HandlingState.ANALYSE_LOGGED),
        ("<ctl ret='ok' />", HandlingState.ANALYSE_LOGGED),
        ("<ctl ret='ok' speed='invalid'/>", HandlingState.ERROR),
    ],
    ids=["error", "no_state", "invalid_speed"],
)
async def test_get_fan_speed_error(xml: str, expected_state: HandlingState) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetCleanSpeed(),
        json,
        None,
        command_result=CommandResult(expected_state),
    )


@pytest.mark.parametrize(
    ("command", "xml", "result"),
    [
        (
            SetCleanSpeed(FanSpeedLevel.MAX),
            "<ctl ret='ok' />",
            HandlingState.SUCCESS,
        ),
    ],
)
async def test_set_fan_speed(
    command: CommandWithMessageHandling, xml: str, result: HandlingState
) -> None:
    json = get_request_xml(xml)
    await assert_command(command, json, None, command_result=CommandResult(result))
