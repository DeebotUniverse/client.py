from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, call

import orjson
import pytest

from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.event_bus import EventBus
from deebot_client.events import FirmwareEvent, StateEvent
from deebot_client.events.station import State as StationState, StationEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json.work_state import OnWorkState
from deebot_client.models import State as RobotState
from tests.helpers.tasks import block_till_done
from tests.messages import assert_message_failure
from tests.messages.json import assert_message

if TYPE_CHECKING:
    from deebot_client.events.base import Event


_X11_MANUAL_MOVEMENT_SEQUENCE = (
    Path(__file__).parents[2] / "data" / "work_state" / "x11_manual_movement.json"
)


@pytest.mark.parametrize(
    ("paused", "robot_state", "additional_content", "station_state", "expected"),
    [
        (
            0,
            "idle",
            {},
            "idle",
            [StationEvent(StationState.IDLE)],
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
        {
            "paused": 0,
            "robotState": {"state": "moving", "trigger": "app"},
            "stationState": {"state": "anotherUnknownState", "trigger": "app"},
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


def test_onWorkState_malformed_robot_state_retains_failure_handling() -> None:
    data = {
        "header": {"fwVer": "1.30.0"},
        "body": {
            "data": {
                "paused": 0,
                "robotState": [],
                "stationState": {"state": "idle", "trigger": "app"},
            }
        },
    }

    assert_message_failure(
        OnWorkState, data, HandlingState.ERROR, FirmwareEvent("1.30.0")
    )


def test_onWorkState_moving_paused_does_not_bypass_docked_guard() -> None:
    message = orjson.loads(_X11_MANUAL_MOVEMENT_SEQUENCE.read_bytes())["messages"][0][
        "payload"
    ]
    message = deepcopy(message)
    message["body"]["data"]["paused"] = 1
    event_bus = Mock(spec_set=EventBus)

    result = OnWorkState.handle(event_bus, message)

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_has_calls(
        [
            call(FirmwareEvent("1.84.0")),
            call(StateEvent(RobotState.PAUSED)),
            call(StationEvent(StationState.IDLE)),
        ]
    )
    assert event_bus.notify.call_count == 3


async def test_onWorkState_x11_manual_movement_sequence(event_bus: EventBus) -> None:
    """Replay the captured manual movement sequence through handlers and EventBus."""
    captured_sequence = orjson.loads(_X11_MANUAL_MOVEMENT_SEQUENCE.read_bytes())[
        "messages"
    ]
    received_states: list[StateEvent] = []

    async def on_state(event: StateEvent) -> None:
        received_states.append(event)

    event_bus.subscribe(StateEvent, on_state)
    event_bus.notify(StateEvent(RobotState.DOCKED))
    await block_till_done(event_bus._tasks)

    for index, message in enumerate(captured_sequence):
        handler = (
            OnWorkState
            if message["message_name"] == OnWorkState.NAME
            else GetChargeState
        )
        result = handler.handle(event_bus, message["payload"])
        assert result.state == HandlingState.SUCCESS
        await block_till_done(event_bus._tasks)

        if index == 5:
            assert event_bus.get_last_event(StateEvent) == StateEvent(
                RobotState.RETURNING
            )

    assert received_states == [
        StateEvent(RobotState.DOCKED),
        StateEvent(RobotState.IDLE),
        StateEvent(RobotState.RETURNING),
        StateEvent(RobotState.DOCKED),
    ]
    assert event_bus.get_last_event(StateEvent) == StateEvent(RobotState.DOCKED)


async def test_onWorkState_docked_idle_and_charging_stay_docked(
    event_bus: EventBus,
) -> None:
    captured_sequence = orjson.loads(_X11_MANUAL_MOVEMENT_SEQUENCE.read_bytes())[
        "messages"
    ]
    received_states: list[StateEvent] = []

    async def on_state(event: StateEvent) -> None:
        received_states.append(event)

    event_bus.subscribe(StateEvent, on_state)
    event_bus.notify(StateEvent(RobotState.DOCKED))
    await block_till_done(event_bus._tasks)

    OnWorkState.handle(event_bus, captured_sequence[3]["payload"])
    GetChargeState.handle(event_bus, captured_sequence[6]["payload"])
    await block_till_done(event_bus._tasks)

    assert received_states == [StateEvent(RobotState.DOCKED)]
    assert event_bus.get_last_event(StateEvent) == StateEvent(RobotState.DOCKED)
