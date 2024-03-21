from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.xml import GetPos
from deebot_client.events import PositionsEvent, PositionType, Position
from deebot_client.message import HandlingState
from tests.commands import assert_command

from . import get_request_xml

if TYPE_CHECKING:
    from deebot_client.events.base import Event


async def test_get_pos() -> None:
    json = get_request_xml(f"<ctl ret='ok' t='p' p='77,-5' a='-3' valid='1'/>")
    expected_event = PositionsEvent(positions=[Position(type=PositionType.DEEBOT, x=77, y=-5)])
    await assert_command(GetPos(), json, expected_event)


@pytest.mark.parametrize(
    "xml",
    ["<ctl ret='error'/>", "<ctl ret='ok' t='p'></ctl>"],
    ids=["error", "no_state"],
)
async def test_get_pos_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetPos(),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )
