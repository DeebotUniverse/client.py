from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.json import GetPos
from deebot_client.events import Position, PositionsEvent, PositionType
from deebot_client.message import HandlingState
from tests.helpers import get_request_json, get_success_body

from . import assert_command

if TYPE_CHECKING:
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("positions", "expected_event", "expected_state"),
    [
        (
            {"none": "none"},
            None,
            HandlingState.ANALYSE_LOGGED,
        ),
        (
            {"deebotPos": {"x": 127, "y": 316, "a": 666, "invalid": 0}},
            PositionsEvent([Position(PositionType("deebotPos"), 127, 316)]),
            HandlingState.SUCCESS,
        ),
        (
            {"chargePos": [{"x": 127, "y": 316, "a": 666}]},
            PositionsEvent([Position(PositionType("chargePos"), 127, 316)]),
            HandlingState.SUCCESS,
        ),
        (
            {
                "deebotPos": {"x": 127, "y": 316, "a": 666, "invalid": 0},
                "chargePos": [{"x": 127, "y": 316, "a": 666}],
            },
            PositionsEvent(
                [
                    Position(PositionType("deebotPos"), 127, 316),
                    Position(PositionType("chargePos"), 127, 316),
                ]
            ),
            HandlingState.SUCCESS,
        ),
    ],
)
async def test_GetPos(
    positions: dict[str, Any] | None,
    expected_event: Event | None,
    expected_state: HandlingState,
) -> None:
    json = get_request_json(get_success_body(positions))
    await assert_command(
        GetPos(), json, expected_event, command_result=CommandResult(expected_state)
    )
