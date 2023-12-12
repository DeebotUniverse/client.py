from collections.abc import Sequence

import pytest

from deebot_client.commands.xml import GetError
from deebot_client.events import ErrorEvent, StateEvent
from deebot_client.events.base import Event
from deebot_client.models import State

from . import assert_command, get_request_xml


@pytest.mark.parametrize(
    ("errs", "expected_events"),
    [
        ("", ErrorEvent(0, "NoError: Robot is operational")),
        ("105", [StateEvent(State.ERROR), ErrorEvent(105, "Stuck: Robot is stuck")]),
    ],
)
async def test_getErrors(errs: str, expected_events: Event | Sequence[Event]) -> None:
    json = get_request_xml(f"<ctl ret='ok' errs='{errs}'/>")
    await assert_command(GetError(), json, expected_events)
