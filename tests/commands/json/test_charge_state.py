from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.commands.json import GetChargeState
from deebot_client.events import StateEvent
from deebot_client.message import HandlingState
from deebot_client.models import State
from tests.helpers import get_message_json, get_request_json, get_success_body

from . import assert_command

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus
    from deebot_client.events import FirmwareEvent
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (get_request_json(get_success_body({"isCharging": 0, "mode": "slot"})), None),
    ],
)
async def test_GetChargeState(
    data: tuple[dict[str, Any], FirmwareEvent], expected: StateEvent | None
) -> None:
    json, firmware_event = data
    events: list[Event] = [firmware_event]
    if expected:
        events.append(expected)
    await assert_command(GetChargeState(), json, events)


@pytest.mark.parametrize(
    "state", [State.CLEANING, State.PAUSED, State.RETURNING, State.ERROR]
)
async def test_noncharging_does_not_overwrite_existing_state(
    event_bus: EventBus, state: State
) -> None:
    event_bus.notify(StateEvent(state))
    message, _ = get_message_json(
        get_success_body({"isCharging": 0, "mode": "autoEmpty"})
    )

    result = GetChargeState.handle(event_bus, message)

    assert result.state == HandlingState.SUCCESS
    assert event_bus.get_last_event(StateEvent) == StateEvent(state)
