from __future__ import annotations

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.xml import GetLifeSpan
from deebot_client.events import LifeSpanEvent, LifeSpan
from deebot_client.message import HandlingState
from tests.commands import assert_command

from . import get_request_xml


@pytest.mark.parametrize(
    ("component_type", "lifespan_type", "left", "total", "expected_event"),
    [
        ("Brush", LifeSpan.BRUSH, 50, 100, LifeSpanEvent(LifeSpan.BRUSH, 50, 50)),
        ("DustCaseHeap", LifeSpan.DUST_CASE_HEAP, 50, 200, LifeSpanEvent(LifeSpan.DUST_CASE_HEAP, 25, 50)),
        ("SideBrush", LifeSpan.SIDE_BRUSH, 25, 200, LifeSpanEvent(LifeSpan.SIDE_BRUSH, 12.5, 25)),
    ],
)
async def test_get_life_span(component_type: str, lifespan_type: LifeSpan, left: int, total: int, expected_event: LifeSpanEvent) -> None:
    json = get_request_xml(f"<ctl ret='ok' type='{component_type}' left='{left}' total='{total}'/>")
    await assert_command(GetLifeSpan(lifespan_type), json, expected_event)


@pytest.mark.parametrize(
    "xml",
    ["<ctl ret='error'/>", "<ctl ret='ok' type='SideBrush' left='123' />"],
    ids=["error", "no_state"],
)
async def test_get_life_span_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetLifeSpan(LifeSpan.BRUSH),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )
