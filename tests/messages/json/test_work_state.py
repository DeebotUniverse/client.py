from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.events import FirmwareEvent, StateEvent
from deebot_client.events.station import State as StationState, StationEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json.work_state import OnWorkState
from deebot_client.models import State as RobotState
from tests.messages import assert_message_failure
from tests.messages.json import assert_message

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("paused", "robot_state", "additional_content", "station_state", "expected"),
    [
        (
            0,
            "idle",
            {},
            "idle",
            [StateEvent(RobotState.IDLE), StationEvent(StationState.IDLE)],
        ),
        (
            1,
            "idle",
            {},
            "idle",
            [StateEvent(RobotState.PAUSED), StationEvent(StationState.IDLE)],
        ),
        (
            0,
            "idle",
            {},
            "goCharging",
            [StateEvent(RobotState.RETURNING), StationEvent(StationState.IDLE)],
        ),
        (
            0,
            "idle",
            {},
            "goEmptying",
            [StateEvent(RobotState.RETURNING), StationEvent(StationState.IDLE)],
        ),
        (
            0,
            "idle",
            {},
            "emptying",
            [
                StateEvent(RobotState.DOCKED),
                StationEvent(StationState.EMPTYING_DUSTBIN),
            ],
        ),
        (
            0,
            "idle",
            {},
            "washing",
            [StateEvent(RobotState.DOCKED), StationEvent(StationState.WASHING_MOP)],
        ),
        (
            0,
            "idle",
            {},
            "drying",
            [StateEvent(RobotState.DOCKED), StationEvent(StationState.DRYING_MOP)],
        ),
        (
            0,
            "cleaning",
            {"cleanState": {"cid": "122", "type": "freeClean"}},
            "idle",
            [StateEvent(RobotState.CLEANING), StationEvent(StationState.IDLE)],
        ),
        (
            0,
            "cleaning",
            {"cleanState": {"cid": "122", "type": "freeClean"}},
            "goCharging",
            [StateEvent(RobotState.RETURNING), StationEvent(StationState.IDLE)],
        ),
        (
            0,
            "cleaning",
            {"cleanState": {"cid": "122", "type": "freeClean"}},
            "goEmptying",
            [StateEvent(RobotState.RETURNING), StationEvent(StationState.IDLE)],
        ),
        (
            0,
            "cleaning",
            {"cleanState": {"cid": "122", "type": "freeClean"}},
            "emptying",
            [
                StateEvent(RobotState.DOCKED),
                StationEvent(StationState.EMPTYING_DUSTBIN),
            ],
        ),
        (
            0,
            "cleaning",
            {"cleanState": {"cid": "122", "type": "freeClean"}},
            "washing",
            [StateEvent(RobotState.DOCKED), StationEvent(StationState.WASHING_MOP)],
        ),
        (
            1,
            "cleaning",
            {"cleanState": {"cid": "122", "type": "freeClean"}},
            "idle",
            [StateEvent(RobotState.PAUSED), StationEvent(StationState.IDLE)],
        ),
    ],
)
@pytest.mark.benchmark
def test_onWorkState(
    paused: int,
    robot_state: str,
    additional_content: dict[str, Any],
    station_state: str,
    expected: list[Event],
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
                "paused": paused,
                "robotState": {
                    "state": robot_state,
                    "trigger": "app",
                    **additional_content,
                },
                "stationState": {
                    "state": station_state,
                    "trigger": "app",
                },
            },
        },
    }

    assert_message(OnWorkState, data, (FirmwareEvent("1.30.0"), *expected))


@pytest.mark.parametrize(
    "message_data",
    [
        {
            "paused": 0,
            "robotState": {
                "state": "unknownState",
                "trigger": "app",
            },
            "stationState": {"state": "anotherUnknownState", "trigger": "app"},
        },
        {
            "paused": 0,
        },
        {
            "paused": 0,
            "robotState": {
                "state": "cleaning",
                "trigger": "app",
            },
        },
        {
            "paused": 0,
            "stationState": {"state": "emptying", "trigger": "app"},
        },
    ],
)
@pytest.mark.benchmark
def test_onWorkState_edge_cases(message_data: dict[str, Any]) -> None:
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
        "body": {"data": message_data},
    }

    assert_message_failure(
        OnWorkState, data, HandlingState.ANALYSE_LOGGED, FirmwareEvent("1.30.0")
    )


def _idle_work_state() -> dict[str, Any]:
    return {
        "paused": 0,
        "robotState": {"state": "idle", "trigger": "app"},
        "stationState": {"state": "idle", "trigger": "app"},
    }


async def test_idle_report_does_not_clear_an_existing_docked_state(
    event_bus: EventBus,
) -> None:
    """A first idle report is real. A later idle report keeps an existing dock."""
    result = OnWorkState._handle_body_data_dict(event_bus, _idle_work_state())
    assert result.state == HandlingState.SUCCESS
    assert event_bus.get_last_event(StateEvent) == StateEvent(RobotState.IDLE)
    assert event_bus.get_last_event(StationEvent) == StationEvent(StationState.IDLE)

    event_bus.notify(StateEvent(RobotState.DOCKED))
    result = OnWorkState._handle_body_data_dict(event_bus, _idle_work_state())
    assert result.state == HandlingState.SUCCESS
    assert event_bus.get_last_event(StateEvent) == StateEvent(RobotState.DOCKED)
    assert event_bus.get_last_event(StationEvent) == StationEvent(StationState.IDLE)
