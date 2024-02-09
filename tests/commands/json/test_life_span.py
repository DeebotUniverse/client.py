from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import GetLifeSpan
from deebot_client.commands.json.life_span import ResetLifeSpan
from deebot_client.events import LifeSpan, LifeSpanEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_execute_command


@pytest.mark.parametrize(
    ("command", "json", "expected"),
    [
        (
            GetLifeSpan(
                {
                    LifeSpan.BRUSH,
                    LifeSpan.FILTER,
                    LifeSpan.SIDE_BRUSH,
                    LifeSpan.UNIT_CARE,
                    LifeSpan.ROUND_MOP,
                    LifeSpan.AIR_FRESHENER,
                    LifeSpan.UV_SANITIZER,
                    LifeSpan.HUMIDIFY,
                    LifeSpan.HUMIDIFY_MAINTENANCE,
                }
            ),
            get_request_json(
                get_success_body(
                    [
                        {"type": "brush", "left": 17979, "total": 18000},
                        {"type": "heap", "left": 7179, "total": 7200},
                        {"type": "sideBrush", "left": 8977, "total": 9000},
                        {"type": "unitCare", "left": 265, "total": 1800},
                        {"type": "roundMop", "left": 6820, "total": 9000},
                        {"type": "dModule", "left": 17537, "total": 18000},
                        {"type": "uv", "left": 898586, "total": 900000},
                        {"type": "humidify", "left": 191547, "total": 194400},
                        {"type": "wbCare", "left": 22260, "total": 43200},
                    ]
                )
            ),
            [
                LifeSpanEvent(LifeSpan.BRUSH, 99.88, 17979),
                LifeSpanEvent(LifeSpan.FILTER, 99.71, 7179),
                LifeSpanEvent(LifeSpan.SIDE_BRUSH, 99.74, 8977),
                LifeSpanEvent(LifeSpan.UNIT_CARE, 14.72, 265),
                LifeSpanEvent(LifeSpan.ROUND_MOP, 75.78, 6820),
                LifeSpanEvent(LifeSpan.AIR_FRESHENER, 97.43, 17537),
                LifeSpanEvent(LifeSpan.UV_SANITIZER, 99.84, 898586),
                LifeSpanEvent(LifeSpan.HUMIDIFY, 98.53, 191547),
                LifeSpanEvent(LifeSpan.HUMIDIFY_MAINTENANCE, 51.53, 22260),
            ],
        ),
        (
            GetLifeSpan({LifeSpan.BRUSH}),
            get_request_json(
                get_success_body([{"type": "brush", "left": 17979, "total": 18000}])
            ),
            [LifeSpanEvent(LifeSpan.BRUSH, 99.88, 17979)],
        ),
        (
            GetLifeSpan([LifeSpan.FILTER]),
            get_request_json(
                get_success_body([{"type": "heap", "left": 7179, "total": 7200}])
            ),
            [LifeSpanEvent(LifeSpan.FILTER, 99.71, 7179)],
        ),
        (
            GetLifeSpan([LifeSpan.SIDE_BRUSH]),
            get_request_json(
                get_success_body([{"type": "sideBrush", "left": 8977, "total": 9000}])
            ),
            [LifeSpanEvent(LifeSpan.SIDE_BRUSH, 99.74, 8977)],
        ),
        (
            GetLifeSpan({LifeSpan.UNIT_CARE}),
            get_request_json(
                get_success_body([{"type": "unitCare", "left": 265, "total": 1800}])
            ),
            [LifeSpanEvent(LifeSpan.UNIT_CARE, 14.72, 265)],
        ),
        (
            GetLifeSpan({LifeSpan.ROUND_MOP}),
            get_request_json(
                get_success_body([{"type": "roundMop", "left": 6820, "total": 9000}])
            ),
            [LifeSpanEvent(LifeSpan.ROUND_MOP, 75.78, 6820)],
        ),
        (
            GetLifeSpan({LifeSpan.AIR_FRESHENER}),
            get_request_json(
                get_success_body([{"type": "dModule", "left": 17537, "total": 18000}])
            ),
            [LifeSpanEvent(LifeSpan.AIR_FRESHENER, 97.43, 17537)],
        ),
        (
            GetLifeSpan({LifeSpan.UV_SANITIZER}),
            get_request_json(
                get_success_body([{"type": "uv", "left": 898586, "total": 900000}])
            ),
            [LifeSpanEvent(LifeSpan.UV_SANITIZER, 99.84, 898586)],
        ),
        (
            GetLifeSpan({LifeSpan.HUMIDIFY}),
            get_request_json(
                get_success_body(
                    [{"type": "humidify", "left": 191547, "total": 194400}]
                )
            ),
            [LifeSpanEvent(LifeSpan.HUMIDIFY, 98.53, 191547)],
        ),
        (
            GetLifeSpan({LifeSpan.HUMIDIFY_MAINTENANCE}),
            get_request_json(
                get_success_body([{"type": "wbCare", "left": 22260, "total": 43200}])
            ),
            [LifeSpanEvent(LifeSpan.HUMIDIFY_MAINTENANCE, 51.53, 22260)],
        ),
    ],
)
async def test_GetLifeSpan(
    command: GetLifeSpan, json: dict[str, Any], expected: list[LifeSpanEvent]
) -> None:
    await assert_command(command, json, expected)


@pytest.mark.parametrize(
    ("command", "args"),
    [
        (ResetLifeSpan(LifeSpan.FILTER), {"type": LifeSpan.FILTER.value}),
        (
            ResetLifeSpan.create_from_mqtt({"type": "brush"}),
            {"type": LifeSpan.BRUSH.value},
        ),
    ],
)
async def test_ResetLifeSpan(command: ResetLifeSpan, args: dict[str, str]) -> None:
    await assert_execute_command(command, args)
