from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.commands.json import GetError
from deebot_client.events import ErrorEvent, StateEvent
from deebot_client.models import State
from tests.helpers import get_request_json, get_success_body

from . import assert_command

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("code", "expected_events"),
    [
        (0, ErrorEvent(0, "NoError: Robot is operational")),
        (105, [StateEvent(State.ERROR), ErrorEvent(105, "Stuck: Robot is stuck")]),
    ],
)
async def test_getErrors(code: int, expected_events: Event | Sequence[Event]) -> None:
    json = get_request_json(get_success_body({"code": [code]}))
    await assert_command(GetError(), json, expected_events)
