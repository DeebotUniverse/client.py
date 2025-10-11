from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import GetPos
from deebot_client.events import Position, PositionsEvent
from deebot_client.rs.map import PositionType
from tests.helpers import get_request_json, get_success_body

from . import assert_command


@pytest.mark.parametrize(
    ("response_data", "expected_positions"),
    [
        (
            {"chargePos": {"x": 5, "y": 9}, "deebotPos": {"x": 1, "y": 5, "a": 85}},
            [
                Position(type=PositionType.DEEBOT, x=1, y=5, a=85),
                Position(type=PositionType.CHARGER, x=5, y=9, a=0),
            ],
        ),
        (
            {
                "chargePos": [{"a": -91, "invalid": 0, "t": 3, "x": 5, "y": 649}],
                "deebotPos": {"a": 0, "invalid": 1, "x": 0, "y": 0},
            },
            [Position(type=PositionType.CHARGER, x=5, y=649, a=-91)],
        ),
        (
            {
                "deebotPos": {"x": -379, "y": -359, "a": 43, "invalid": 0},
                "chargePos": [{"x": -379, "y": -359, "a": 43, "t": 3, "invalid": 0}],
            },
            [
                Position(type=PositionType.DEEBOT, x=-379, y=-359, a=43),
                Position(type=PositionType.CHARGER, x=-379, y=-359, a=43),
            ],
        ),
    ],
)
async def test_GetPos(
    response_data: dict[str, Any], expected_positions: list[Position]
) -> None:
    json, firmware_event = get_request_json(get_success_body(response_data))
    expected_events = (
        firmware_event,
        PositionsEvent(positions=expected_positions),
    )
    await assert_command(GetPos(), json, expected_events)
