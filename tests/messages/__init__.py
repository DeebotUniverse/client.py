from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

from deebot_client.event_bus import EventBus
from deebot_client.message import HandlingState, Message

if TYPE_CHECKING:
    from deebot_client.events import Event


def assert_message(
    message: type[Message], data: dict[str, Any], expected_event: Event
) -> None:
    event_bus = Mock(spec_set=EventBus)

    result = message.handle(event_bus, data)

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(expected_event)
