from __future__ import annotations

import pytest

from deebot_client.events import ChildLockEvent, FirmwareEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json.child_lock import OnChildLock
from tests.messages.json import assert_message


@pytest.mark.parametrize(
    ("on", "expected"),
    [(0, False), (1, True), (2, True), ("0", False), ("1", True)],
)
@pytest.mark.benchmark
def test_onChildLock(on: object, expected: bool) -> None:
    data = {
        "header": {
            "pri": 1,
            "tzm": 60,
            "ts": "1734719921057",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {"data": {"on": on}},
    }

    assert_message(
        OnChildLock,
        data,
        (FirmwareEvent("1.8.2"), ChildLockEvent(expected)),
        device_class="55uoqe",
    )


@pytest.mark.parametrize("value", ["false", None, 2.0, [1]])
@pytest.mark.benchmark
def test_onChildLock_unknown(value: object) -> None:
    """Unrepresentable values must not fabricate a latch state."""
    data = {
        "header": {
            "pri": 1,
            "tzm": 60,
            "ts": "1734719921057",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {"data": {"on": value}},
    }

    assert_message(
        OnChildLock,
        data,
        (FirmwareEvent("1.8.2"),),
        expected_state=HandlingState.ANALYSE_LOGGED,
        device_class="55uoqe",
    )
