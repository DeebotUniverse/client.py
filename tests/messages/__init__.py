from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING
from unittest.mock import Mock, call

from deebot_client.event_bus import EventBus
from deebot_client.hardware import get_static_device_info
from deebot_client.message import (
    HandlingResult,
    HandlingState,
    Message,
    MessagePayloadType,
)

if TYPE_CHECKING:
    from deebot_client.events import Event


async def assert_message(
    message: type[Message],
    data: MessagePayloadType,
    expected_events: Event | None | Sequence[Event],
    *,
    device_class: str,
    expected_state: HandlingState = HandlingState.SUCCESS,
) -> HandlingResult:
    event_bus = Mock(spec_set=EventBus)
    static_device_info = await get_static_device_info(device_class)
    assert static_device_info is not None, f"Unknown device class: {device_class}"
    event_bus.capabilities = static_device_info.capabilities

    result = message.handle(event_bus, data)

    assert result.state == expected_state
    if expected_events:
        if isinstance(expected_events, Sequence):
            event_bus.notify.assert_has_calls([call(x) for x in expected_events])
            assert event_bus.notify.call_count == len(expected_events)
        else:
            event_bus.notify.assert_called_once_with(expected_events)
    else:
        event_bus.notify.assert_not_called()

    return result


def assert_message_failure(
    message: type[Message],
    data: MessagePayloadType,
    expected_result_state: HandlingState,
    expected_events: Event | None | Sequence[Event] = None,
) -> None:
    event_bus = Mock(spec_set=EventBus)

    result = message.handle(event_bus, data)

    assert result.state == expected_result_state
    if expected_events:
        if isinstance(expected_events, Sequence):
            event_bus.notify.assert_has_calls([call(x) for x in expected_events])
            assert event_bus.notify.call_count == len(expected_events)
        else:
            event_bus.notify.assert_called_once_with(expected_events)
    else:
        event_bus.notify.assert_not_called()
