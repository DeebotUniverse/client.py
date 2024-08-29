from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.xml import GetCleanSum
from deebot_client.events import TotalStatsEvent
from deebot_client.message import HandlingState
from tests.commands import assert_command

from . import get_request_xml

if TYPE_CHECKING:
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("area", "lifetime", "count", "expected_event"),
    [
        (1000, 20, 30, TotalStatsEvent(1000, 20, 30)),
    ],
)
async def test_get_clean_sum(
    area: int, lifetime: int, count: int, expected_event: Event
) -> None:
    json = get_request_xml(f"<ctl ret='ok' a='{area}' l='{lifetime}' c='{count}' />")
    await assert_command(GetCleanSum(), json, expected_event)


@pytest.mark.parametrize(
    "xml",
    ["<ctl ret='error'/>", "<ctl ret='ok' a='34' />"],
    ids=["error", "error"],
)
async def test_get_clean_sum_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetCleanSum(),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )
