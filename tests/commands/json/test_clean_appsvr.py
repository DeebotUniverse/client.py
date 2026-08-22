"""Tests for CleanAppSvr command."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from deebot_client.commands.json.clean_appsvr import CleanAppSvr
from deebot_client.event_bus import EventBus
from deebot_client.events import StateEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import CleanAction, State


def _handle(action: CleanAction, ret: str = "ok") -> tuple[Mock, HandlingResult]:
    event_bus = Mock(spec_set=EventBus)
    cmd = CleanAppSvr(action)
    result = cmd._handle_response(event_bus, {"ret": ret})
    return event_bus, result


@pytest.mark.parametrize("action", [CleanAction.START, CleanAction.RESUME])
def test_clean_start_resume_fires_cleaning(action: CleanAction) -> None:
    event_bus, result = _handle(action)
    event_bus.notify.assert_called_once_with(StateEvent(State.CLEANING))
    assert result == HandlingResult.success()


@pytest.mark.parametrize("action", [CleanAction.PAUSE, CleanAction.STOP])
def test_clean_pause_stop_fires_paused(action: CleanAction) -> None:
    event_bus, result = _handle(action)
    event_bus.notify.assert_called_once_with(StateEvent(State.PAUSED))
    assert result == HandlingResult.success()


@pytest.mark.parametrize("action", list(CleanAction))
def test_clean_failed(action: CleanAction) -> None:
    event_bus, result = _handle(action, ret="fail")
    event_bus.notify.assert_not_called()
    assert result.state == HandlingState.FAILED
