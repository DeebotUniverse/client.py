from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from deebot_client.event_bus import EventBus
from deebot_client.events import FirmwareEvent, StateEvent
from deebot_client.events.station import State, StationEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json.station_state import OnStationState
from deebot_client.models import State as RobotState
from tests.messages.json import assert_message


@pytest.mark.parametrize(
    ("state", "additional_content", "expected"),
    [
        (0, {"type": 0}, State.IDLE),
        (1, {"type": 1, "motionState": 1}, State.EMPTYING_DUSTBIN),
        (1, {"type": 2, "motionState": 1}, State.DRYING_MOP),
    ],
)
@pytest.mark.benchmark
def test_onStationState(
    state: int,
    additional_content: dict[str, Any],
    expected: State,
) -> None:
    data: dict[str, Any] = {
        "header": {
            "pri": 1,
            "tzm": 60,
            "ts": "1734719921057",
            "ver": "0.0.1",
            "fwVer": "1.30.0",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {
            "data": {
                "content": {"error": [], **additional_content},
                "state": state,
            },
            "code": 0,
            "msg": "ok",
        },
    }

    assert_message(
        OnStationState,
        data,
        (FirmwareEvent("1.30.0"), StationEvent(expected)),
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
@pytest.mark.benchmark
def test_onStationState_analyse(
    state: int,
    additional_content: dict[str, Any],
) -> None:
    """Cases that should fall through to analyse() (not handled)."""
    data: dict[str, Any] = {
        "header": {
            "pri": 1,
            "tzm": 60,
            "ts": "1734719921057",
            "ver": "0.0.1",
            "fwVer": "1.30.0",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {
            "data": {
                "content": {"error": [], **additional_content},
                "state": state,
            },
            "code": 0,
            "msg": "ok",
        },
    }

    assert_message(
        OnStationState,
        data,
        (FirmwareEvent("1.30.0"),),
        expected_state=HandlingState.ANALYSE_LOGGED,
    )


def test_onStationState_preserves_washing_mop() -> None:
    """Test X2 OMNI station idle does not overwrite active mop washing."""
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.side_effect = (
        StationEvent(State.WASHING_MOP),
        StateEvent(RobotState.CLEANING),
    )

    data = {
        "content": {
            "error": [314],
            "motionState": 0,
            "subContent": {
                "handEmpty": {
                    "charging": 0,
                    "connect": 0,
                    "emptying": 1,
                    "powerFull": 0,  # codespell:ignore
                }
            },
            "type": 0,
        },
        "state": 0,
    }

    result = OnStationState._handle_body_data_dict(event_bus, data)

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(StationEvent(State.WASHING_MOP))
