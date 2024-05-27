from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import GetLifeSpan
from deebot_client.commands.json.life_span import ResetLifeSpan
from deebot_client.events import LifeSpan, LifeSpanEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_command_response, assert_execute_command


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
                    LifeSpan.DUST_BAG,
                    LifeSpan.CLEANING_FLUID,
                    LifeSpan.STRAINER,
                    LifeSpan.HAND_FILTER,
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
                        {
                            "type": "autoWater_cleaningFluid",
                            "left": 86400,
                            "total": 86400,
                        },
                        {"type": "dustBag", "left": 2031, "total": 3000},
                        {"type": "handFilter", "left": 30000, "total": 30000},
                        {"type": "strainer", "left": 1800, "total": 1800},
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
                LifeSpanEvent(LifeSpan.CLEANING_FLUID, 100.0, 86400),
                LifeSpanEvent(LifeSpan.DUST_BAG, 67.7, 2031),
                LifeSpanEvent(LifeSpan.HAND_FILTER, 100.0, 30000),
                LifeSpanEvent(LifeSpan.STRAINER, 100.0, 1800),
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
        (
            GetLifeSpan({LifeSpan.CLEANING_FLUID}),
            get_request_json(
                get_success_body(
                    [{"type": "autoWater_cleaningFluid", "left": 86400, "total": 86400}]
                )
            ),
            [LifeSpanEvent(LifeSpan.CLEANING_FLUID, 100.0, 86400)],
        ),
        (
            GetLifeSpan({LifeSpan.DUST_BAG}),
            get_request_json(
                get_success_body([{"type": "dustBag", "left": 2031, "total": 3000}])
            ),
            [LifeSpanEvent(LifeSpan.DUST_BAG, 67.7, 2031)],
        ),
        (
            GetLifeSpan({LifeSpan.HAND_FILTER}),
            get_request_json(
                get_success_body(
                    [{"type": "handFilter", "left": 30000, "total": 30000}]
                )
            ),
            [LifeSpanEvent(LifeSpan.HAND_FILTER, 100.0, 30000)],
        ),
        (
            GetLifeSpan({LifeSpan.STRAINER}),
            get_request_json(
                get_success_body([{"type": "strainer", "left": 1800, "total": 1800}])
            ),
            [LifeSpanEvent(LifeSpan.STRAINER, 100.0, 1800)],
        ),
    ],
)
async def test_GetLifeSpan(
    command: GetLifeSpan, json: dict[str, Any], expected: list[LifeSpanEvent]
) -> None:
    await assert_command(command, json, expected)


@pytest.mark.parametrize(
    ("command", "json"),
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
                    LifeSpan.DUST_BAG,
                    LifeSpan.CLEANING_FLUID,
                    LifeSpan.STRAINER,
                    LifeSpan.HAND_FILTER,
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
                        {
                            "type": "autoWater_cleaningFluid",
                            "left": 86400,
                            "total": 86400,
                        },
                        {"type": "dustBag", "left": 2031, "total": 3000},
                        {"type": "handFilter", "left": 30000, "total": 30000},
                        {"type": "strainer", "left": 1800, "total": 1800},
                    ]
                )
            ),
        ),
        (
            GetLifeSpan({LifeSpan.BRUSH}),
            get_request_json(
                get_success_body([{"type": "brush", "left": 17979, "total": 18000}])
            ),
        ),
        (
            GetLifeSpan([LifeSpan.FILTER]),
            get_request_json(
                get_success_body([{"type": "heap", "left": 7179, "total": 7200}])
            ),
        ),
        (
            GetLifeSpan([LifeSpan.SIDE_BRUSH]),
            get_request_json(
                get_success_body([{"type": "sideBrush", "left": 8977, "total": 9000}])
            ),
        ),
        (
            GetLifeSpan({LifeSpan.UNIT_CARE}),
            get_request_json(
                get_success_body([{"type": "unitCare", "left": 265, "total": 1800}])
            ),
        ),
        (
            GetLifeSpan({LifeSpan.ROUND_MOP}),
            get_request_json(
                get_success_body([{"type": "roundMop", "left": 6820, "total": 9000}])
            ),
        ),
        (
            GetLifeSpan({LifeSpan.AIR_FRESHENER}),
            get_request_json(
                get_success_body([{"type": "dModule", "left": 17537, "total": 18000}])
            ),
        ),
        (
            GetLifeSpan({LifeSpan.UV_SANITIZER}),
            get_request_json(
                get_success_body([{"type": "uv", "left": 898586, "total": 900000}])
            ),
        ),
        (
            GetLifeSpan({LifeSpan.HUMIDIFY}),
            get_request_json(
                get_success_body(
                    [{"type": "humidify", "left": 191547, "total": 194400}]
                )
            ),
        ),
        (
            GetLifeSpan({LifeSpan.HUMIDIFY_MAINTENANCE}),
            get_request_json(
                get_success_body([{"type": "wbCare", "left": 22260, "total": 43200}])
            ),
        ),
        (
            GetLifeSpan({LifeSpan.CLEANING_FLUID}),
            get_request_json(
                get_success_body(
                    [{"type": "autoWater_cleaningFluid", "left": 86400, "total": 86400}]
                )
            ),
        ),
        (
            GetLifeSpan({LifeSpan.DUST_BAG}),
            get_request_json(
                get_success_body([{"type": "dustBag", "left": 2031, "total": 3000}])
            ),
        ),
        (
            GetLifeSpan({LifeSpan.HAND_FILTER}),
            get_request_json(
                get_success_body(
                    [{"type": "handFilter", "left": 30000, "total": 30000}]
                )
            ),
        ),
        (
            GetLifeSpan({LifeSpan.STRAINER}),
            get_request_json(
                get_success_body([{"type": "strainer", "left": 1800, "total": 1800}])
            ),
        ),
    ],
)
async def test_GetLifeSpan_response(command: GetLifeSpan, json: dict[str, Any]) -> None:
    await assert_command_response(command, json, json.get("resp"))


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
