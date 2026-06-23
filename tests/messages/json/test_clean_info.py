from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.events import FirmwareEvent, StateEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json.clean_info import OnScheduleTaskInfo
from deebot_client.models import State
from tests.messages import assert_message_failure
from tests.messages.json import assert_message

if TYPE_CHECKING:
    from deebot_client.events.base import Event


def _wrap(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "header": {
            "pri": 1,
            "tzm": 120,
            "ts": "1782211281022726164",
            "ver": "0.0.1",
            "fwVer": "1.9.16",
            "hwVer": "0.1.1",
        },
        "body": {"data": data},
    }


@pytest.mark.parametrize(
    ("state", "clean_state", "expected"),
    [
        ("clean", {"motionState": "working"}, StateEvent(State.CLEANING)),
        ("clean", {"motionState": "pause"}, StateEvent(State.PAUSED)),
        ("clean", {"motionState": "goCharging"}, StateEvent(State.RETURNING)),
        ("goCharging", None, StateEvent(State.RETURNING)),
        ("idle", None, StateEvent(State.IDLE)),
    ],
)
@pytest.mark.benchmark
def test_onScheduleTaskInfo(
    state: str, clean_state: dict[str, Any] | None, expected: Event
) -> None:
    # Scheduled mows are reported via onScheduleTaskInfo, which carries the same
    # payload shape as onCleanInfo (a top-level state plus nested
    # cleanState.motionState).
    data: dict[str, Any] = {"trigger": "continue", "other": "0", "state": state}
    if clean_state is not None:
        data["cleanState"] = clean_state
    assert_message(OnScheduleTaskInfo, _wrap(data), (FirmwareEvent("1.9.16"), expected))


@pytest.mark.parametrize("state", ["unknownState", ""])
@pytest.mark.benchmark
def test_onScheduleTaskInfo_ignored_states(state: str) -> None:
    data = {"trigger": "continue", "state": state}
    assert_message_failure(
        OnScheduleTaskInfo,
        _wrap(data),
        HandlingState.ANALYSE_LOGGED,
        FirmwareEvent("1.9.16"),
    )


@pytest.mark.benchmark
def test_onScheduleTaskInfo_alert_maps_to_error() -> None:
    # trigger "alert" maps to ERROR regardless of the reported state
    data = {"trigger": "alert", "state": "clean"}
    assert_message(
        OnScheduleTaskInfo,
        _wrap(data),
        (FirmwareEvent("1.9.16"), StateEvent(State.ERROR)),
    )
