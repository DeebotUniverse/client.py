from __future__ import annotations

from typing import Any

import pytest

from deebot_client.events import FirmwareEvent
from deebot_client.events.station import State, StationErrorEvent, StationEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json.station_state import OnStationState
from tests.messages.json import assert_message

_HEADER = {
    "pri": 1,
    "tzm": 60,
    "ts": "1734719921057",
    "ver": "0.0.1",
    "fwVer": "1.30.0",
    "hwVer": "0.1.1",
    "wkVer": "0.1.54",
}


def _payload(data: dict[str, Any]) -> dict[str, Any]:
    return {"header": dict(_HEADER), "body": {"data": data, "code": 0, "msg": "ok"}}


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
    data = _payload({"content": {"error": [], **additional_content}, "state": state})

    assert_message(
        OnStationState,
        data,
        (FirmwareEvent("1.30.0"), StationErrorEvent(()), StationEvent(expected)),
    )


@pytest.mark.parametrize(
    ("state", "additional_content"),
    [
        # no type or motionState
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
def test_onStationState_analyse(state: int, additional_content: dict[str, Any]) -> None:
    """Cases that fall through to analyse() (not handled).

    The error channel is still reported, so an unrecognised state does not
    swallow a station fault.
    """
    data = _payload({"content": {"error": [], **additional_content}, "state": state})

    assert_message(
        OnStationState,
        data,
        (FirmwareEvent("1.30.0"), StationErrorEvent(())),
        expected_state=HandlingState.ANALYSE_LOGGED,
    )


@pytest.mark.benchmark
def test_onStationState_error_not_a_list() -> None:
    """A non-list error field means 'unknown', not 'no errors'."""
    data = _payload({"content": {"error": "301", "type": 0}, "state": 0})
    assert_message(
        OnStationState,
        data,
        (FirmwareEvent("1.30.0"), StationEvent(State.IDLE)),
    )


@pytest.mark.benchmark
def test_onStationState_without_content() -> None:
    """A frame without a content/error channel must not assert 'no errors'."""
    data = _payload({"state": 0})
    assert_message(
        OnStationState,
        data,
        (FirmwareEvent("1.30.0"), StationEvent(State.IDLE)),
    )


@pytest.mark.benchmark
def test_onStationState_without_error_field() -> None:
    """Content without an error key means 'unknown', not 'no errors'."""
    data = _payload({"content": {"type": 0}, "state": 0})
    assert_message(
        OnStationState,
        data,
        (FirmwareEvent("1.30.0"), StationEvent(State.IDLE)),
    )


@pytest.mark.benchmark
def test_onStationState_string_error_codes() -> None:
    """Error codes sent as strings are coerced to ints."""
    data = _payload({"content": {"error": ["301", "302"], "type": 0}, "state": 0})
    assert_message(
        OnStationState,
        data,
        (
            FirmwareEvent("1.30.0"),
            StationErrorEvent((301, 302)),
            StationEvent(State.IDLE),
        ),
    )


@pytest.mark.benchmark
def test_onStationState_unrecognised_state_keeps_errors() -> None:
    """A valid error tuple survives an unrecognised activity state."""
    data = _payload(
        {"content": {"error": [301], "type": 99, "motionState": 1}, "state": 1}
    )
    assert_message(
        OnStationState,
        data,
        (FirmwareEvent("1.30.0"), StationErrorEvent((301,))),
        expected_state=HandlingState.ANALYSE_LOGGED,
    )


@pytest.mark.parametrize("errors", [[301], [301, 314], [305, 318, 323]])
@pytest.mark.benchmark
def test_onStationState_errors(errors: list[int]) -> None:
    """Station error codes are surfaced when the state is known."""
    data = _payload({"content": {"error": errors, "type": 0}, "state": 0})
    assert_message(
        OnStationState,
        data,
        (
            FirmwareEvent("1.30.0"),
            StationErrorEvent(tuple(errors)),
            StationEvent(State.IDLE),
        ),
    )


@pytest.mark.parametrize("error", [[True], [3.0], ["x"], [{"code": 301}]])
@pytest.mark.benchmark
def test_onStationState_unparseable_errors_are_ignored(error: list[Any]) -> None:
    """A non-empty but unusable error list is unknown, not 'no errors'."""
    data = _payload({"content": {"error": error, "type": 0}, "state": 0})
    assert_message(
        OnStationState,
        data,
        (FirmwareEvent("1.30.0"), StationEvent(State.IDLE)),
    )


@pytest.mark.benchmark
def test_onStationState_mixed_error_entries() -> None:
    """Only usable entries are kept; unusable ones are skipped."""
    data = _payload(
        {"content": {"error": [True, 301, "302", 3.0], "type": 0}, "state": 0}
    )
    assert_message(
        OnStationState,
        data,
        (
            FirmwareEvent("1.30.0"),
            StationErrorEvent((301, 302)),
            StationEvent(State.IDLE),
        ),
    )
