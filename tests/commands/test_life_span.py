from typing import Any

import pytest

from deebot_client.commands import GetLifeSpan
from deebot_client.events import LifeSpan, LifeSpanEvent
from tests.commands import assert_command_requested
from tests.helpers import get_request_json


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
def test_GetLifeSpan(json: dict[str, Any], expected: list[LifeSpanEvent]) -> None:
    assert_command_requested(GetLifeSpan(), json, expected)
