from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from deebot_client.commands.json.work_state import GetWorkState
from deebot_client.commands.json.xwk78e import GetWorkStateT80
from deebot_client.events import StateEvent
from deebot_client.events.station import State as StationState, StationEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import State as RobotState
from tests.helpers import get_request_json, get_success_body

from . import assert_command

if TYPE_CHECKING:
    from deebot_client.events.base import Event


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
async def test_GetWorkState(
    paused: int,
    robot_state: str,
    additional_content: dict[str, Any],
    station_state: str,
    expected: list[Event],
) -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "paused": paused,
                "robotState": {
                    "state": robot_state,
                    "trigger": "app",
                    **additional_content,
                },
                "stationState": {"state": station_state, "trigger": "app"},
            }
        )
    )
    await assert_command(GetWorkState(), json, (firmware_event, *expected))


async def test_GetWorkState_does_not_override_docked_with_stale_pause() -> None:
    event_bus = Mock()
    event_bus.get_last_event.return_value = StateEvent(RobotState.IDLE)

    result = GetWorkStateT80._handle_body_data_dict(
        event_bus,
        {
            "paused": 1,
            "robotState": {"state": "cleaning", "trigger": "voice"},
            "stationState": {"state": "idle"},
        },
    )

    assert result == HandlingResult.success()
    event_bus.notify.assert_called_once_with(StationEvent(StationState.IDLE))


@pytest.mark.parametrize(
    "request_data",
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
async def test_GetWorkState_edge_cases(request_data: dict[str, Any]) -> None:
    json, firmware_event = get_request_json(get_success_body(request_data))
    await assert_command(
        GetWorkState(),
        json,
        firmware_event,
        handling_result=HandlingResult(HandlingState.ANALYSE_LOGGED),
    )
