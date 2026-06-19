"""Tests for OnPos and OnCleanInfo mower telemetry push handlers."""

from __future__ import annotations

import pytest

from deebot_client.events import StateEvent
from deebot_client.events.map import Position, PositionsEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json.mower_telemetry import OnCleanInfo, OnPos
from deebot_client.models import State
from deebot_client.rs.map import PositionType
from tests.messages.json import assert_message


def _body(data: dict) -> dict:
    return {
        "header": {"tzm": -420, "ts": "1781463003383", "fwVer": "1.13.31"},
        "body": {"data": data},
    }


# ---------------------------------------------------------------------------
# OnPos
# ---------------------------------------------------------------------------

@pytest.mark.benchmark
def test_onPos_deebot_and_charge_positions() -> None:
    """Both deebotPos and chargePos present → two Position objects in event."""
    data = _body({
        "deebotPos": {"x": -1234, "y": 567, "a": 270, "invalid": 0},
        "chargePos": [{"x": 0, "y": 0, "a": 0}],
    })
    assert_message(
        OnPos,
        data,
        PositionsEvent(positions=[
            Position(type=PositionType.from_str("deebotPos"), x=-1234, y=567, a=270),
            Position(type=PositionType.from_str("chargePos"), x=0, y=0, a=0),
        ]),
    )


@pytest.mark.benchmark
def test_onPos_invalid_gps_fix_skipped() -> None:
    """Entries with invalid=1 must be skipped; event only contains valid ones."""
    data = _body({
        "deebotPos": {"x": 100, "y": 200, "a": 90, "invalid": 1},  # invalid
        "chargePos": [{"x": 0, "y": 0, "a": 0}],                   # valid
    })
    assert_message(
        OnPos,
        data,
        PositionsEvent(positions=[
            Position(type=PositionType.from_str("chargePos"), x=0, y=0, a=0),
        ]),
    )


@pytest.mark.benchmark
def test_onPos_all_invalid_returns_analyse() -> None:
    """If all positions are invalid, HandlingResult should be ANALYSE (no event)."""
    data = _body({"deebotPos": {"x": 0, "y": 0, "a": 0, "invalid": 1}})
    assert_message(OnPos, data, None, expected_state=HandlingState.ANALYSE)


@pytest.mark.benchmark
def test_onPos_missing_fields_returns_analyse() -> None:
    """Empty payload → no positions → ANALYSE result."""
    assert_message(OnPos, _body({}), None, expected_state=HandlingState.ANALYSE)


@pytest.mark.benchmark
def test_onPos_chargePos_as_dict() -> None:
    """chargePos can arrive as a dict (not list) and should still be parsed."""
    data = _body({
        "chargePos": {"x": 10, "y": 20, "a": 0},
    })
    assert_message(
        OnPos,
        data,
        PositionsEvent(positions=[
            Position(type=PositionType.from_str("chargePos"), x=10, y=20, a=0),
        ]),
    )


# ---------------------------------------------------------------------------
# OnCleanInfo
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("payload", "expected_state"),
    [
        (
            {"trigger": "alert", "state": "clean"},
            State.ERROR,
        ),
        (
            {"state": "clean", "cleanState": {"motionState": "working"}},
            State.CLEANING,
        ),
        (
            {"state": "washing", "cleanState": {"motionState": "working"}},
            State.CLEANING,
        ),
        (
            {"state": "clean", "cleanState": {"motionState": "pause"}},
            State.PAUSED,
        ),
        (
            {"state": "clean", "cleanState": {"motionState": "goCharging"}},
            State.RETURNING,
        ),
        (
            {"state": "goCharging"},
            State.RETURNING,
        ),
        (
            {"state": "idle"},
            State.IDLE,
        ),
    ],
    ids=["alert", "cleaning", "washing", "paused", "returning-via-motionstate", "returning-via-state", "idle"],
)
@pytest.mark.benchmark
def test_onCleanInfo_state_mapping(payload: dict, expected_state: State) -> None:
    assert_message(OnCleanInfo, _body(payload), StateEvent(expected_state))


@pytest.mark.benchmark
def test_onCleanInfo_unknown_state_returns_analyse() -> None:
    """Unrecognised state → ANALYSE (no event fired)."""
    assert_message(
        OnCleanInfo,
        _body({"state": "unknown_future_state"}),
        None,
        expected_state=HandlingState.ANALYSE,
    )


@pytest.mark.benchmark
def test_onCleanInfo_empty_payload_returns_analyse() -> None:
    assert_message(OnCleanInfo, _body({}), None, expected_state=HandlingState.ANALYSE)
