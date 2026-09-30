from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest

from deebot_client.commands.json import GetError
from deebot_client.events import ErrorEvent, StateEvent
from deebot_client.messages.json.charge_info import OnChargeInfo
from deebot_client.models import State
from tests.helpers import get_request_json, get_success_body

from . import assert_command

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deebot_client.event_bus import EventBus
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("body", "expected_events"),
    [
        ({"code": [0]}, (ErrorEvent(0, "NoError: Robot is operational"),)),
        ({"code": []}, (ErrorEvent(0, "NoError: Robot is operational"),)),
        (
            {"code": [105]},
            (StateEvent(State.ERROR), ErrorEvent(105, "Stuck: Robot is stuck")),
        ),
    ],
)
async def test_getErrors(
    body: dict[str, Any], expected_events: Sequence[Event]
) -> None:
    json, firmware_event = get_request_json(get_success_body(body))
    await assert_command(GetError(), json, (firmware_event, *expected_events))


@pytest.mark.parametrize("device_class", ["300lc5", "yna5xi"])
@pytest.mark.parametrize("codes", [[], [0]])
@pytest.mark.parametrize("previous_error", [None, 105, 0])
@pytest.mark.parametrize("state", [State.ERROR, State.CLEANING])
async def test_error_clear_refreshes_mower_activity_without_duplicate_reads(
    event_bus: EventBus,
    device_class: str,
    codes: list[int],
    previous_error: int | None,
    state: State,
) -> None:
    if previous_error is not None:
        event_bus.notify(ErrorEvent(previous_error, None))
    event_bus.notify(StateEvent(state))
    event_bus.subscribe(StateEvent, AsyncMock())
    with patch.object(event_bus, "request_refresh") as refresh:
        GetError.handle(event_bus, {"body": {"data": {"code": codes}}})
        if device_class == "300lc5" and state is State.ERROR:
            refresh.assert_called_once_with(StateEvent, queue_if_busy=True)
        else:
            refresh.assert_not_called()
        # Clearing an error must query real activity, never invent mowing or idle.
        assert event_bus.get_last_event(StateEvent) == StateEvent(state)
        assert event_bus.get_last_event(ErrorEvent) == ErrorEvent(
            0, "NoError: Robot is operational"
        )
        refresh.reset_mock()
        GetError.handle(event_bus, {"body": {"data": {"code": codes}}})
        refresh.assert_not_called()
    await event_bus.teardown()


@pytest.mark.parametrize("device_class", ["300lc5"])
async def test_error_recovery_for_each_alert_episode(event_bus: EventBus) -> None:
    """A status alert can arrive while the last error-code report is still zero."""
    clear: dict[str, Any] = {"body": {"data": {"code": []}}}
    GetError.handle(event_bus, clear)
    event_bus.notify(StateEvent(State.CLEANING))
    event_bus.subscribe(StateEvent, AsyncMock())
    with patch.object(event_bus, "request_refresh") as refresh:
        for _ in range(2):
            event_bus.notify(StateEvent(State.CLEANING))
            OnChargeInfo.handle(
                event_bus, {"body": {"data": {"trigger": "alert", "state": "idle"}}}
            )
            GetError.handle(event_bus, clear)
            refresh.assert_called_once_with(StateEvent, queue_if_busy=True)
            assert event_bus.get_last_event(StateEvent) == StateEvent(State.ERROR)
            GetError.handle(event_bus, clear)
            refresh.assert_called_once()
            refresh.reset_mock()
    await event_bus.teardown()


@pytest.mark.parametrize("device_class", ["300lc5"])
async def test_error_recovery_after_new_fault_while_still_in_error(
    event_bus: EventBus,
) -> None:
    """A new fault clearance needs a read even if earlier recovery stayed ERROR."""
    event_bus.notify(StateEvent(State.ERROR))
    event_bus.subscribe(StateEvent, AsyncMock())
    clear: dict[str, Any] = {"body": {"data": {"code": []}}}
    with patch.object(event_bus, "request_refresh") as refresh:
        GetError.handle(event_bus, clear)
        refresh.assert_called_once_with(StateEvent, queue_if_busy=True)
        GetError.handle(event_bus, {"body": {"data": {"code": [105]}}})
        refresh.reset_mock()
        GetError.handle(event_bus, clear)
        refresh.assert_called_once_with(StateEvent, queue_if_busy=True)
        GetError.handle(event_bus, clear)
        refresh.assert_called_once()
    await event_bus.teardown()


@pytest.mark.parametrize("device_class", ["300lc5"])
async def test_active_mower_error_is_not_cleared(event_bus: EventBus) -> None:
    event_bus.notify(StateEvent(State.CLEANING))
    with patch.object(event_bus, "request_refresh") as refresh:
        GetError.handle(event_bus, {"body": {"data": {"code": [105]}}})
        assert event_bus.get_last_event(StateEvent) == StateEvent(State.ERROR)
        refresh.assert_not_called()
