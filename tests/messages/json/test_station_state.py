from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from deebot_client.commands.json.station_state import GetStationState
from deebot_client.event_bus import EventBus
from deebot_client.events import StateEvent
from deebot_client.events.station import State, StationEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.messages.json.station_state import OnStationState
from deebot_client.models import State as RobotState
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


async def test_station_idle_preserves_washing_mop() -> None:
    """Test X2 OMNI station idle does not overwrite active mop washing."""
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.side_effect = (
        StationEvent(State.WASHING_MOP),
        StateEvent(RobotState.CLEANING),
    )

    data = {
        "content": {
            "error": [],
            "type": 0,
        },
        "state": 0,
    }

    result = OnStationState._handle_body_data_dict(event_bus, data)

    assert result == HandlingResult.success()
    event_bus.notify.assert_called_once_with(StationEvent(State.WASHING_MOP))
