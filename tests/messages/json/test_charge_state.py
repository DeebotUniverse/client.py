from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.events import FirmwareEvent, StateEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json.charge_state import OnChargeInfo
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
            "ts": "1782211283816888165",
            "ver": "0.0.1",
            "fwVer": "1.9.16",
            "hwVer": "0.1.1",
        },
        "body": {"data": data},
    }


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("goCharging", StateEvent(State.RETURNING)),
        ("idle", StateEvent(State.DOCKED)),
    ],
)
@pytest.mark.benchmark
def test_onChargeInfo(state: str, expected: Event) -> None:
    # GOAT mowers report return/dock transitions via onChargeInfo: the top-level
    # state is "goCharging" while returning and "idle" once work completes.
    data = {"cid": "122", "trigger": "app", "state": state, "other": "0"}
    assert_message(OnChargeInfo, _wrap(data), (FirmwareEvent("1.9.16"), expected))


@pytest.mark.parametrize("state", ["clean", "unknownState", ""])
@pytest.mark.benchmark
def test_onChargeInfo_ignored_states(state: str) -> None:
    data = {"cid": "122", "trigger": "app", "state": state}
    assert_message_failure(
        OnChargeInfo,
        _wrap(data),
        HandlingState.ANALYSE_LOGGED,
        FirmwareEvent("1.9.16"),
    )
