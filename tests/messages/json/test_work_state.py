from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.commands.json.charge_state import GetChargeState
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


def _work_state(robot: str, station: str, paused: int = 0) -> dict[str, Any]:
    return {
        "paused": paused,
        "robotState": {"state": robot, "trigger": "app"},
        "stationState": {"state": station, "trigger": "app"},
    }


async def _watch(event_bus: EventBus) -> list[RobotState]:
    seen: list[RobotState] = []

    async def record(event: StateEvent) -> None:
        seen.append(event.state)

    event_bus.subscribe(StateEvent, record)
    await asyncio.sleep(0)
    return seen


async def _work(event_bus: EventBus, robot: str, station: str, paused: int = 0) -> None:
    result = OnWorkState._handle_body_data_dict(
        event_bus, _work_state(robot, station, paused)
    )
    assert result.state == HandlingState.SUCCESS
    await asyncio.sleep(0)


async def _charge(event_bus: EventBus, is_charging: int) -> None:
    result = GetChargeState._handle_body_data_dict(
        event_bus, {"isCharging": is_charging}
    )
    assert result.state == HandlingState.SUCCESS
    await asyncio.sleep(0)


async def test_restart_idle_is_real_and_duplicates_are_ignored(
    event_bus: EventBus,
) -> None:
    """No stored activity: idle is idle. A repeat and isCharging=0 add nothing."""
    seen = await _watch(event_bus)

    await _work(event_bus, "idle", "idle")
    await _work(event_bus, "idle", "idle")
    await _charge(event_bus, 0)

    assert seen == [RobotState.IDLE]
    assert event_bus.get_last_event(StateEvent) == StateEvent(RobotState.IDLE)
    assert event_bus.get_last_event(StationEvent) == StationEvent(StationState.IDLE)


async def test_charge_and_idle_order_keeps_an_existing_dock(
    event_bus: EventBus,
) -> None:
    """Either order may establish a dock. Later idle reports do not remove it."""
    seen = await _watch(event_bus)

    await _charge(event_bus, 1)
    await _work(event_bus, "idle", "idle")
    await _work(event_bus, "idle", "idle")
    await _charge(event_bus, 0)

    assert seen == [RobotState.DOCKED]
    assert event_bus.get_last_event(StateEvent) == StateEvent(RobotState.DOCKED)
    assert event_bus.get_last_event(StationEvent) == StationEvent(StationState.IDLE)


async def test_idle_then_charge_docks_and_later_idle_stays_docked(
    event_bus: EventBus,
) -> None:
    seen = await _watch(event_bus)

    await _work(event_bus, "idle", "idle")
    await _charge(event_bus, 1)
    await _work(event_bus, "idle", "idle")
    await _charge(event_bus, 1)

    assert seen == [RobotState.IDLE, RobotState.DOCKED]
    assert event_bus.get_last_event(StateEvent) == StateEvent(RobotState.DOCKED)


async def test_real_activity_replaces_idle_and_docked_without_duplicates(
    event_bus: EventBus,
) -> None:
    """Cleaning, returning, and paused pass through. Idle afterwards is not a dock."""
    seen = await _watch(event_bus)

    await _work(event_bus, "cleaning", "idle")
    await _work(event_bus, "cleaning", "idle")
    await _work(event_bus, "idle", "goCharging")
    await _work(event_bus, "idle", "goEmptying")
    await _work(event_bus, "cleaning", "idle", paused=1)
    await _work(event_bus, "cleaning", "idle", paused=1)
    await _work(event_bus, "idle", "idle")
    event_bus.notify(StateEvent(RobotState.ERROR))
    await asyncio.sleep(0)
    event_bus.notify(StateEvent(RobotState.ERROR))
    await asyncio.sleep(0)
    await _work(event_bus, "cleaning", "idle")
    await _work(event_bus, "idle", "idle")

    assert seen == [
        RobotState.CLEANING,
        RobotState.RETURNING,
        RobotState.PAUSED,
        RobotState.IDLE,
        RobotState.ERROR,
        RobotState.CLEANING,
        RobotState.IDLE,
    ]
    assert event_bus.get_last_event(StateEvent) == StateEvent(RobotState.IDLE)
    assert event_bus.get_last_event(StationEvent) == StationEvent(StationState.IDLE)


async def test_station_work_reports_docked_and_following_idle_keeps_it(
    event_bus: EventBus,
) -> None:
    seen = await _watch(event_bus)

    await _work(event_bus, "idle", "emptying")
    await _work(event_bus, "cleaning", "washing")
    await _work(event_bus, "idle", "drying")
    await _work(event_bus, "idle", "idle")
    await _work(event_bus, "cleaning", "idle")
    await _work(event_bus, "idle", "washing")
    await _work(event_bus, "idle", "idle")

    assert seen == [RobotState.DOCKED, RobotState.CLEANING, RobotState.DOCKED]
    assert event_bus.get_last_event(StateEvent) == StateEvent(RobotState.DOCKED)
    assert event_bus.get_last_event(StationEvent) == StationEvent(StationState.IDLE)


async def test_paused_on_dock_is_explicit_and_unpaused_idle_is_not_a_dock(
    event_bus: EventBus,
) -> None:
    seen = await _watch(event_bus)

    await _charge(event_bus, 1)
    await _work(event_bus, "idle", "idle", paused=1)
    await _work(event_bus, "idle", "idle")

    assert seen == [RobotState.DOCKED, RobotState.PAUSED, RobotState.IDLE]
    assert event_bus.get_last_event(StateEvent) == StateEvent(RobotState.IDLE)


async def test_unknown_work_pair_does_not_change_a_dock_or_emit_idle(
    event_bus: EventBus,
) -> None:
    """moving+idle belongs to the separate manual-movement change, not this one."""
    seen = await _watch(event_bus)
    await _charge(event_bus, 1)

    result = OnWorkState._handle_body_data_dict(
        event_bus, _work_state("moving", "idle")
    )
    await asyncio.sleep(0)

    assert result.state == HandlingState.ANALYSE
    assert seen == [RobotState.DOCKED]
    assert event_bus.get_last_event(StateEvent) == StateEvent(RobotState.DOCKED)
