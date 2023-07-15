import asyncio
from collections.abc import Callable
from unittest.mock import AsyncMock, call

import pytest

from deebot_client.events import AvailabilityEvent, BatteryEvent, StateEvent
from deebot_client.events.base import Event
from deebot_client.events.const import EVENT_DTO_REFRESH_COMMANDS
from deebot_client.events.event_bus import EventBus
from deebot_client.models import VacuumState


def _verify_event_command_called(
    execute_mock: AsyncMock, event: type[Event], expected_call: bool
) -> None:
    for command in EVENT_DTO_REFRESH_COMMANDS[event]:
        if expected_call:
            assert call(command) in execute_mock.call_args_list
        else:
            execute_mock.assert_not_called()


async def _subscribeAndVerify(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    to_subscribe: type[Event],
    expected_call: bool,
) -> Callable[[], None]:
    unsubscribe = event_bus.subscribe(to_subscribe, AsyncMock())

    await asyncio.sleep(0.1)
    _verify_event_command_called(execute_mock, to_subscribe, expected_call)

    execute_mock.reset_mock()
    return unsubscribe


@pytest.mark.parametrize("event", [BatteryEvent, StateEvent])
async def test_subscription(
    execute_mock: AsyncMock, event_bus: EventBus, event: type[Event]
) -> None:
    # on first should subscription the refresh should be triggered
    unsubscribers = [await _subscribeAndVerify(execute_mock, event_bus, event, True)]

    # this time no refresh should be happen
    unsubscribers.append(
        await _subscribeAndVerify(execute_mock, event_bus, event, False)
    )

    # unscubscrbe from all
    for unsubscribe in unsubscribers:
        unsubscribe()

    # as there are no subscriber...
    # the first one, should trigger a refresh
    await _subscribeAndVerify(execute_mock, event_bus, event, True)


async def test_refresh_when_coming_back_online(
    execute_mock: AsyncMock, event_bus: EventBus
) -> None:
    available_mock = AsyncMock()

    async def notify(available: bool) -> None:
        event = AvailabilityEvent(available)
        event_bus.notify(event)
        await asyncio.sleep(0.1)
        available_mock.assert_awaited_with(event)

    event_bus.subscribe(BatteryEvent, AsyncMock())
    event_bus.subscribe(StateEvent, AsyncMock())
    event_bus.subscribe(AvailabilityEvent, available_mock)
    await asyncio.sleep(0.1)

    # Only calls made after coming back online are of interest
    execute_mock.reset_mock()

    await notify(False)
    await notify(True)

    _verify_event_command_called(execute_mock, BatteryEvent, True)
    _verify_event_command_called(execute_mock, StateEvent, True)
    _verify_event_command_called(execute_mock, AvailabilityEvent, False)


async def test_get_last_event(event_bus: EventBus) -> None:
    def notify(percent: int) -> BatteryEvent:
        event = BatteryEvent(percent)
        event_bus.notify(event)
        assert event_bus.get_last_event(BatteryEvent) == event
        return event

    assert event_bus.get_last_event(BatteryEvent) is None

    event = notify(100)

    event_bus.subscribe(BatteryEvent, AsyncMock())
    assert event_bus.get_last_event(BatteryEvent) == event

    notify(10)


async def test_request_refresh(execute_mock: AsyncMock, event_bus: EventBus) -> None:
    event = BatteryEvent
    event_bus.request_refresh(event)
    _verify_event_command_called(execute_mock, event, False)

    event_bus.subscribe(event, AsyncMock())
    execute_mock.reset_mock()

    event_bus.request_refresh(event)

    await asyncio.sleep(0.1)
    _verify_event_command_called(execute_mock, event, True)


@pytest.mark.parametrize(
    "last, actual, expected",
    [
        (VacuumState.DOCKED, VacuumState.IDLE, VacuumState.DOCKED),
        (VacuumState.CLEANING, VacuumState.IDLE, VacuumState.IDLE),
        (VacuumState.IDLE, VacuumState.DOCKED, VacuumState.DOCKED),
    ],
)
async def test_StateEvent(
    event_bus: EventBus, last: VacuumState, actual: VacuumState, expected: VacuumState
) -> None:
    async def notify(state: VacuumState) -> None:
        event_bus.notify(StateEvent(state))
        await asyncio.sleep(0.1)

    await notify(last)

    mock = AsyncMock()
    event_bus.subscribe(StateEvent, mock)

    await notify(actual)

    mock.assert_called_once_with(StateEvent(expected))
