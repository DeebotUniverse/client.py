from __future__ import annotations

from typing import cast
from unittest.mock import Mock

from deebot_client.commands.ngiot.error import GetError
from deebot_client.event_bus import EventBus
from deebot_client.events import ErrorEvent
from deebot_client.message import HandlingState


def test_get_error_notifies_non_zero_error() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetError.handle(
        cast("EventBus", event_bus),
        {"body": {"data": {"error": [5]}}},
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(ErrorEvent(5, "NGIOT error 5"))


def test_get_error_zero_error_is_success_without_event() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetError.handle(
        cast("EventBus", event_bus),
        {"body": {"data": {"error": [0]}}},
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_not_called()
