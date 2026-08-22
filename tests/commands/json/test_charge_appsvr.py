"""Tests for ChargeAppSvr command."""

from __future__ import annotations

from unittest.mock import Mock

from deebot_client.commands.json.charge_appsvr import ChargeAppSvr
from deebot_client.event_bus import EventBus
from deebot_client.events import StateEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import State


def _handle(ret: str = "ok") -> tuple[Mock, HandlingResult]:
    event_bus = Mock(spec_set=EventBus)
    cmd = ChargeAppSvr()
    result = cmd._handle_response(event_bus, {"ret": ret})
    return event_bus, result


def test_charge_returns_to_dock() -> None:
    event_bus, result = _handle("ok")
    event_bus.notify.assert_called_once_with(StateEvent(State.RETURNING))
    assert result == HandlingResult.success()


def test_charge_failed() -> None:
    event_bus, result = _handle("fail")
    event_bus.notify.assert_not_called()
    assert result.state == HandlingState.FAILED
