from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.events import Position, PositionsEvent, PositionType
from deebot_client.message import HandlingState
from deebot_client.messages.json import OnPos
from tests.helpers import get_message_json, get_success_body
from tests.messages import assert_message

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
    ],
)
async def test_OnPos(
    positions: dict[str, Any] | None,
    expected_event: Event | None,
    expected_state: HandlingState,
) -> None:
    json = get_message_json(get_success_body(positions))
    assert_message(OnPos, json, expected_event, expected_state=expected_state)
