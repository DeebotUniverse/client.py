from __future__ import annotations

from typing import TYPE_CHECKING, Any

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
    ("body", "expected_events"),
    [
        ({"code": [0]}, ErrorEvent(0, "NoError: Robot is operational")),
        ({"code": []}, ErrorEvent(0, "NoError: Robot is operational")),
        (
            {"code": [105]},
            [StateEvent(State.ERROR), ErrorEvent(105, "Stuck: Robot is stuck")],
        ),
    ],
)
async def test_getErrors(
    body: dict[str, Any], expected_events: Event | Sequence[Event]
) -> None:
    json = get_request_json(get_success_body(body))
    await assert_command(GetError(), json, expected_events)
