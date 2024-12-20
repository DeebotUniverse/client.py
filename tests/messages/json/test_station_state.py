from __future__ import annotations

from typing import Any

import pytest

from deebot_client.events.base_station import BaseStationEvent, Status
from deebot_client.messages.json.station_state import OnStationState
from tests.messages import assert_message


@pytest.mark.parametrize(
    ("state", "additional_content", "expected"),
    [
        (0, {"type": 0}, Status.IDLE),
        (1, {"type": 1, "motionState": 1}, Status.EMPTYING),
    ],
)
def test_onStationState(
    state: int,
    additional_content: dict[str, Any],
    expected: Status,
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
            "data": {"content": {"error": [], **additional_content}, "state": state},
            "code": 0,
            "msg": "ok",
        },
    }

    assert_message(OnStationState, data, BaseStationEvent(expected))
