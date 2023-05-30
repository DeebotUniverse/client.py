import asyncio
from unittest.mock import AsyncMock, call

import pytest

from deebot_client.events import AvailabilityEvent, BatteryEvent, StateEvent
from deebot_client.events.base import Event
from deebot_client.events.const import EVENT_DTO_REFRESH_COMMANDS
from deebot_client.events.event_bus import EventBus, EventListener


async def _subscribeAndVerify(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    to_subscribe: type[Event],
    expected_call: bool,
) -> EventListener:
    listener = event_bus.subscribe(to_subscribe, AsyncMock())

    await asyncio.sleep(0.1)
    for command in EVENT_DTO_REFRESH_COMMANDS[to_subscribe]:
        if expected_call:
            assert call(command) in execute_mock.call_args_list
        else:
            execute_mock.assert_not_called()

    execute_mock.reset_mock()
    return listener


@pytest.mark.parametrize("event", [BatteryEvent, StateEvent])
async def test_subscription(event: type[Event]) -> None:
    execute_mock = AsyncMock()
    event_bus = EventBus(execute_mock)

    # on first should subscription the refresh should be triggered
    listeners = [await _subscribeAndVerify(execute_mock, event_bus, event, True)]

    # this time no refresh should be happen
    listeners.append(await _subscribeAndVerify(execute_mock, event_bus, event, False))

    # unscubscrbe from all
    for listener in listeners:
        listener.unsubscribe()

    # as there are no subscriber...
    # the first one, should trigger a refresh
    await _subscribeAndVerify(execute_mock, event_bus, event, True)


async def test_refresh_when_coming_back_online() -> None:
    available_mock = AsyncMock()

    async def notify(available: bool) -> None:
        event = AvailabilityEvent(available)
        event_bus.notify(event)
        await asyncio.sleep(0.1)
        available_mock.assert_awaited_with(event)

    def verify(event: type[Event], expected_call: bool) -> None:
        for command in EVENT_DTO_REFRESH_COMMANDS[event]:
            if expected_call:
                assert call(command) in execute_mock.call_args_list
            else:
                execute_mock.assert_not_called()

    execute_mock = AsyncMock()
    event_bus = EventBus(execute_mock)

    event_bus.subscribe(BatteryEvent, AsyncMock())
    event_bus.subscribe(StateEvent, AsyncMock())
    event_bus.subscribe(AvailabilityEvent, available_mock)
    await asyncio.sleep(0.1)

    # Only calls made after coming back online are of interest
    execute_mock.reset_mock()

    await notify(False)
    await notify(True)

    verify(BatteryEvent, True)
    verify(StateEvent, True)
    verify(AvailabilityEvent, False)
