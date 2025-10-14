from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json.station_state import GetStationState
from deebot_client.events.station import State, StationEvent
from deebot_client.message import HandlingResult, HandlingState
from tests.helpers import get_request_json, get_success_body

from . import assert_command


@pytest.mark.parametrize(
    ("state", "additional_content", "expected"),
    [
        (0, {"type": 0}, State.IDLE),
        (1, {"type": 1, "motionState": 1}, State.EMPTYING_DUSTBIN),
        (1, {"type": 2, "motionState": 1}, State.DRYING_MOP),
    ],
)
async def test_GetStationState(
    state: int,
    additional_content: dict[str, Any],
    expected: State,
) -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "content": {"error": [], **additional_content},
                "state": state,
            }
        )
    )
    await assert_command(
        GetStationState(), json, (firmware_event, StationEvent(expected))
    )


@pytest.mark.parametrize(
    ("state", "additional_content"),
    [
        # content missing
        (1, {}),
        # type present but motionState missing
        (1, {"type": 2}),
        # type matches but motionState different
        (1, {"type": 2, "motionState": 0}),
        # unexpected state value
        (2, {"type": 2, "motionState": 1}),
    ],
)
async def test_GetStationState_analyse(
    state: int,
    additional_content: dict[str, Any],
) -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "content": {"error": [], **additional_content},
                "state": state,
            }
        )
    )

    await assert_command(
        GetStationState(),
        json,
        firmware_event,
        handling_result=HandlingResult(HandlingState.ANALYSE_LOGGED),
    )
