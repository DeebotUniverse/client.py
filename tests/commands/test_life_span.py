from typing import Any

import pytest

from deebot_client.commands import GetLifeSpan
from deebot_client.commands.life_span import GetLifeSpanBrush, GetLifeSpanSideBrush, GetLifeSpanHeap
from deebot_client.events import LifeSpan, LifeSpanEvent
from tests.commands import assert_command
from tests.helpers import get_request_json, get_request_xml


@pytest.mark.parametrize(
    "json, expected",
    [
        (
            get_request_json(
                [
                    {"type": "sideBrush", "left": 8977, "total": 9000},
                    {"type": "brush", "left": 17979, "total": 18000},
                    {"type": "heap", "left": 7179, "total": 7200},
                ]
            ),
            [
                LifeSpanEvent(LifeSpan.SIDE_BRUSH, 99.74, 8977),
                LifeSpanEvent(LifeSpan.BRUSH, 99.88, 17979),
                LifeSpanEvent(LifeSpan.FILTER, 99.71, 7179),
            ],
        ),
    ],
)
async def test_GetLifeSpan(json: dict[str, Any], expected: list[LifeSpanEvent]) -> None:
    await assert_command(GetLifeSpan(), json, expected)


@pytest.mark.parametrize(
    "json, expected",
    [
        (
            get_request_xml("<ctl ret='ok' type='Brush' left='17979' total='18000'/>"),
            LifeSpanEvent(LifeSpan.BRUSH, 99.88, 17979),
        ),
    ],
)
async def test_GetLifeSpanBrush(json: dict[str, Any], expected: LifeSpanEvent) -> None:
    await assert_command(GetLifeSpanBrush(), json, expected)


@pytest.mark.parametrize(
    "json, expected",
    [
        (
            get_request_xml("<ctl ret='ok' type='SideBrush' left='8977' total='9000'/>"),
            LifeSpanEvent(LifeSpan.SIDE_BRUSH, 99.74, 8977),
        ),
    ],
)
async def test_GetLifeSpanSideBrush(json: dict[str, Any], expected: LifeSpanEvent) -> None:
    await assert_command(GetLifeSpanSideBrush(), json, expected)


@pytest.mark.parametrize(
    "json, expected",
    [
        (
            get_request_xml("<ctl ret='ok' type='DustCaseHeap' left='7179' total='7200'/>"),
            LifeSpanEvent(LifeSpan.FILTER, 99.71, 7179),
        ),
    ],
)
async def test_GetLifeSpanDustCaseHeap(json: dict[str, Any], expected: LifeSpanEvent) -> None:
    await assert_command(GetLifeSpanHeap(), json, expected)
