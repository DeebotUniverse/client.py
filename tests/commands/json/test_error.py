from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.commands.json import GetError
from deebot_client.events import Error, ErrorEvent, StateEvent
from deebot_client.models import State
from tests.helpers import get_request_json, get_success_body

from . import assert_command

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deebot_client.events.base import Event

STUCK = Error(105, "Stuck: Robot is stuck")


@pytest.mark.parametrize(
    ("body", "expected_events"),
    [
        pytest.param({"code": [0]}, (ErrorEvent([]),), id="no_error"),
        pytest.param({"code": []}, (ErrorEvent([]),), id="empty"),
        pytest.param(
            {"code": [105]},
            (StateEvent(State.ERROR), ErrorEvent([STUCK])),
            id="single",
        ),
        pytest.param(
            {"code": [102, 105]},
            (
                StateEvent(State.ERROR),
                ErrorEvent([Error(102, "HostHang: Robot is off the floor"), STUCK]),
            ),
            id="multiple",
        ),
        pytest.param(
            {"code": [105, 0]},
            (StateEvent(State.ERROR), ErrorEvent([STUCK])),
            id="trailing_zero",
        ),
    ],
)
async def test_getErrors(
    body: dict[str, Any], expected_events: Sequence[Event]
) -> None:
    json, firmware_event = get_request_json(get_success_body(body))
    await assert_command(GetError(), json, (firmware_event, *expected_events))
