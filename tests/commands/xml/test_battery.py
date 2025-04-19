from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.xml import GetBatteryInfo
from deebot_client.events import BatteryEvent
from deebot_client.message import HandlingState
from tests.commands import assert_command

from . import get_request_xml

if TYPE_CHECKING:
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("power", "expected_event"),
    [
        (40, BatteryEvent(40)),
    ],
    ids=["40_pct_battery"],
)
async def test_get_battery_info(power: int, expected_event: Event) -> None:
    xml_message = get_request_xml(f"<ctl ret='ok'><battery power='{power}' /></ctl>")
    await assert_command(GetBatteryInfo(), xml_message, expected_event)


@pytest.mark.parametrize(
    "payload",
    [
        '<ctl ret="error"/>',
        '<ctl ret="ok"></ctl>',
        '<ctl ret="ok"><battery /></ctl>',
        '<ctl ret="ok"><test power="1" /></ctl>',
        '<ctl ret="ok"><battery power="-1" /></ctl>',
        '<ctl ret="ok"><battery power="test" /></ctl>',
    ],
    ids=[
        "error",
        "no_state",
        "no_power",
        "wrong_inner_element",
        "negative_power",
        "strange_power_reading",
    ],
)
async def test_get_battery_info_error(payload: str) -> None:
    xml_message = get_request_xml(payload)
    await assert_command(
        GetBatteryInfo(),
        xml_message,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )
