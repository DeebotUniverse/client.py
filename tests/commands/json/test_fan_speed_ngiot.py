"""Tests for SetFanSpeedNgiot command."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from deebot_client.commands.json.fan_speed_ngiot import SetFanSpeedNgiot
from deebot_client.event_bus import EventBus
from deebot_client.events import FanSpeedEvent
from deebot_client.events.fan_speed import FanSpeedLevel
from deebot_client.message import HandlingResult, HandlingState


def _handle(speed: FanSpeedLevel, ret: str = "ok") -> tuple[Mock, HandlingResult]:
    event_bus = Mock(spec_set=EventBus)
    cmd = SetFanSpeedNgiot(speed)
    result = cmd._handle_response(event_bus, {"ret": ret})
    return event_bus, result


@pytest.mark.parametrize(
    "speed",
    [FanSpeedLevel.QUIET, FanSpeedLevel.NORMAL, FanSpeedLevel.MAX, FanSpeedLevel.MAX_PLUS],
)
def test_set_fan_speed_fires_event(speed: FanSpeedLevel) -> None:
    event_bus, result = _handle(speed)
    event_bus.notify.assert_called_once_with(FanSpeedEvent(speed))
    assert result == HandlingResult.success()


@pytest.mark.parametrize(
    "speed",
    [FanSpeedLevel.QUIET, FanSpeedLevel.NORMAL, FanSpeedLevel.MAX, FanSpeedLevel.MAX_PLUS],
)
def test_set_fan_speed_failed(speed: FanSpeedLevel) -> None:
    event_bus, result = _handle(speed, ret="fail")
    event_bus.notify.assert_not_called()
    assert result.state == HandlingState.FAILED


def test_set_fan_speed_from_string() -> None:
    cmd = SetFanSpeedNgiot("QUIET")
    assert cmd._speed == FanSpeedLevel.QUIET
