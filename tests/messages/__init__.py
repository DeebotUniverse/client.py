from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING
from unittest.mock import Mock, call

from deebot_client.event_bus import EventBus
from deebot_client.message import HandlingState, Message, MessagePayloadType

if TYPE_CHECKING:
    from deebot_client.events import Event


def assert_message(
    message: type[Message],
    data: MessagePayloadType,
    expected_events: Event | Sequence[Event],
) -> None:
    event_bus = Mock(spec_set=EventBus)

    result = message.handle(event_bus, data)

    assert result.state == HandlingState.SUCCESS
    if isinstance(expected_events, Sequence):
        event_bus.notify.assert_has_calls([call(x) for x in expected_events])
        assert event_bus.notify.call_count == len(expected_events)
    else:
        event_bus.notify.assert_called_once_with(expected_events)


def assert_message_failure(
    message: type[Message],
    data: MessagePayloadType,
    expected_result_state: HandlingState,
) -> None:
    event_bus = Mock(spec_set=EventBus)

    result = message.handle(event_bus, data)

    assert result.state == expected_result_state
    event_bus.notify.assert_not_called()
