from typing import Any

import pytest

from deebot_client.commands.json import GetLifeSpan
from deebot_client.events import LifeSpan, LifeSpanEvent
from tests.helpers import get_request_json

from . import assert_command


@pytest.mark.parametrize(
    "command, json, expected",
    [
        (
            GetLifeSpan({LifeSpan.BRUSH, LifeSpan.FILTER, LifeSpan.SIDE_BRUSH}),
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
async def test_GetLifeSpan(
    command: GetLifeSpan, json: dict[str, Any], expected: list[LifeSpanEvent]
) -> None:
    await assert_command(command, json, expected)
