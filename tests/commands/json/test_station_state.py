from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json.station_state import GetStationState
from deebot_client.events.station import State, StationEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command


@pytest.mark.parametrize(
    ("state", "additional_content", "expected"),
    [
        (0, {"type": 0}, State.IDLE),
        (1, {"type": 1, "motionState": 1}, State.EMPTYING),
    ],
)
async def test_GetStationState(
    state: int,
    additional_content: dict[str, Any],
    expected: State,
) -> None:
    json = get_request_json(
        get_success_body(
            {
                "content": {"error": [], **additional_content},
                "state": state,
            }
        )
    )
    await assert_command(GetStationState(), json, StationEvent(expected))
