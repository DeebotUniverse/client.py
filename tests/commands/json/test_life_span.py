from typing import Any

import pytest

from deebot_client.commands.json import GetLifeSpan
from deebot_client.commands.json.life_span import LifeSpanType, ResetLifeSpan
from deebot_client.events import LifeSpan, LifeSpanEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_execute_command


@pytest.mark.parametrize(
    "command, json, expected",
    [
        (
            GetLifeSpan({"brush", LifeSpan.FILTER, LifeSpan.SIDE_BRUSH}),
            get_request_json(
                get_success_body(
                    [
                        {"type": "sideBrush", "left": 8977, "total": 9000},
                        {"type": "brush", "left": 17979, "total": 18000},
                        {"type": "heap", "left": 7179, "total": 7200},
                    ]
                )
            ),
            [
                LifeSpanEvent(LifeSpan.SIDE_BRUSH, 99.74, 8977),
                LifeSpanEvent(LifeSpan.BRUSH, 99.88, 17979),
                LifeSpanEvent(LifeSpan.FILTER, 99.71, 7179),
            ],
        ),
        (
            GetLifeSpan(LifeSpan.FILTER),
            get_request_json(
                get_success_body([{"type": "heap", "left": 7179, "total": 7200}])
            ),
            [LifeSpanEvent(LifeSpan.FILTER, 99.71, 7179)],
        ),
        (
            GetLifeSpan("brush"),
            get_request_json(
                get_success_body([{"type": "brush", "left": 17979, "total": 18000}])
            ),
            [LifeSpanEvent(LifeSpan.BRUSH, 99.88, 17979)],
        ),
    ],
)
async def test_GetLifeSpan(
    command: GetLifeSpan, json: dict[str, Any], expected: list[LifeSpanEvent]
) -> None:
    await assert_command(command, json, expected)


@pytest.mark.parametrize(
    "_type, args",
    [
        (LifeSpan.FILTER, {"type": LifeSpan.FILTER.value}),
        ("brush", {"type": LifeSpan.BRUSH.value}),
    ],
)
async def test_ResetLifeSpan(_type: LifeSpanType, args: dict[str, str]) -> None:
    await assert_execute_command(ResetLifeSpan(_type), args)
