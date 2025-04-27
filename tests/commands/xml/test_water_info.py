from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.xml import GetWaterBoxInfo
from deebot_client.events.water_info import MopAttachedEvent
from deebot_client.message import HandlingState
from tests.commands import assert_command

from . import get_request_xml

if TYPE_CHECKING:
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("state", "expected_event"),
    [
        (1, MopAttachedEvent(True)),
        (0, MopAttachedEvent(False)),
    ],
    ids=["mop_attached", "mop_not_attached"],
)
async def test_get_water_box_info(state: int, expected_event: Event) -> None:
    xml_message = get_request_xml(f"<ctl ret='ok' on='{state}' />")
    await assert_command(GetWaterBoxInfo(), xml_message, expected_event)


@pytest.mark.parametrize(
    "payload",
    [
        '<ctl ret="error"/>',
        '<ctl ret="ok"></ctl>',
    ],
    ids=[
        "error",
        "no_state",
    ],
)
async def test_get_water_box_info_error(payload: str) -> None:
    xml_message = get_request_xml(payload)
    await assert_command(
        GetWaterBoxInfo(),
        xml_message,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )
