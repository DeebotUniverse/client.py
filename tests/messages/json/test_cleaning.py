from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from deebot_client.commands.json.clean import GetCleanInfoV2
from deebot_client.events import StateEvent
from deebot_client.events.cleaning import (
    LastCleaningStatsEvent,
    RoomProgress,
    RoomProgressEvent,
)
from deebot_client.events.station import State as StationState, StationEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json import MESSAGES
from deebot_client.models import State


@pytest.mark.parametrize("status", [2, 3, 97])
def test_room_progress_preserves_raw_codes(status: int) -> None:
    bus = Mock()
    result = MESSAGES["onCleanDataUpdate_V2"]._handle_body_data_dict(
        bus,
        {
            "cid": "42",
            "mid": "123",
            "type": "freeClean",
            "content": [{"id": 11, "status": status, "type": 1}],
        },
    )
    assert result.state == HandlingState.SUCCESS
    bus.notify.assert_called_once_with(
        RoomProgressEvent("42", "123", "freeClean", (RoomProgress(11, status, 1),))
    )


@pytest.mark.parametrize(("area", "duration"), [(8, 420), (0, 0)])
def test_final_statistics_do_not_synthesize_success(area: int, duration: int) -> None:
    bus = Mock()
    result = MESSAGES["onLastTimeStats"]._handle_body_data_dict(
        bus,
        {
            "start": "1700000000",
            "area": area,
            "time": duration,
            "type": "freeClean",
        },
    )
    assert result.state == HandlingState.SUCCESS
    bus.notify.assert_called_once_with(
        LastCleaningStatsEvent(1700000000, area, duration, "freeClean")
    )


@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("onCleanDataUpdate_V2", {}),
        ("onCleanDataUpdate_V2", {"content": None}),
        ("onCleanDataUpdate_V2", {"content": [{"id": "bad"}]}),
        ("onLastTimeStats", {}),
        ("onLastTimeStats", {"start": 1, "area": -1, "time": 0, "type": "freeClean"}),
    ],
)
def test_malformed_notifications_do_not_emit(name: str, data: dict[str, Any]) -> None:
    bus = Mock()
    result = MESSAGES[name]._handle_body_data_dict(bus, data)
    assert result.state == HandlingState.ANALYSE
    bus.notify.assert_not_called()


@pytest.mark.parametrize(
    ("state", "motion", "trigger", "expected"),
    [
        ("washing", "working", "none", State.DOCKED),
        ("clean", "working", "none", State.CLEANING),
        ("washing", "pause", "none", State.PAUSED),
        ("washing", "goCharging", "none", State.RETURNING),
        ("washing", "working", "alert", State.ERROR),
    ],
)
def test_washing_state(state: str, motion: str, trigger: str, expected: State) -> None:
    bus = Mock()
    result = GetCleanInfoV2._handle_body_data_dict(
        bus, {"state": state, "cleanState": {"motionState": motion}, "trigger": trigger}
    )
    assert result.state == HandlingState.SUCCESS
    emitted = [c.args[0] for c in bus.notify.call_args_list]
    assert StateEvent(expected) in emitted
    washing = state == "washing" and expected == State.DOCKED
    assert (StationEvent(StationState.WASHING_MOP) in emitted) == washing
