from __future__ import annotations

from deebot_client.commands.json import GetPos
from deebot_client.events import Position, PositionsEvent, PositionType
from tests.helpers import get_request_json, get_success_body

from . import assert_command


async def test_GetPos() -> None:
    json = get_request_json(
        get_success_body(
            {"chargePos": {"x": 5, "y": 9}, "deebotPos": {"x": 1, "y": 5, "a": 85}}
        )
    )
    expected_event = PositionsEvent(
        positions=[
            Position(type=PositionType.DEEBOT, x=1, y=5, a=85),
            Position(type=PositionType.CHARGER, x=5, y=9, a=0),
        ]
    )
    await assert_command(GetPos(), json, expected_event)
