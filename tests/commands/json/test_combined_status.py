"""Tests for GetCombinedStatus command."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from deebot_client.commands.json.combined_status import GetCombinedStatus
from deebot_client.event_bus import EventBus
from deebot_client.events import (
    BatteryEvent,
    ChildLockEvent,
    ErrorEvent,
    FanSpeedEvent,
    LifeSpanEvent,
    StateEvent,
)
from deebot_client.events.fan_speed import FanSpeedLevel
from deebot_client.events.water_info import MopAttachedEvent, WaterAmount, WaterAmountEvent
from deebot_client.message import HandlingResult
from deebot_client.models import LifeSpan, State


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    GetCombinedStatus._cache.clear()


def _handle(data: dict[str, Any] | None = None) -> tuple[Mock, HandlingResult]:
    event_bus = Mock(spec_set=EventBus)
    body: dict[str, Any] = {"code": 0, "msg": "ok"}
    if data is not None:
        body["data"] = data
    result = GetCombinedStatus._handle_body(event_bus, body)
    return event_bus, result


def _notified(event_bus: Mock) -> list[Any]:
    return [c.args[0] for c in event_bus.notify.call_args_list]


def test_docked() -> None:
    event_bus, result = _handle(
        {
            "battery": 100,
            "chargeStatus": True,
            "pauseSwitch": False,
            "workMode": "stop",
            "error": [0],
        }
    )
    events = _notified(event_bus)
    assert BatteryEvent(100) in events
    assert StateEvent(State.DOCKED) in events
    assert ErrorEvent(code=0, description="No error") in events
    assert result == HandlingResult.success()


def test_cleaning() -> None:
    event_bus, _ = _handle(
        {"battery": 80, "chargeStatus": False, "pauseSwitch": False, "workMode": "auto", "error": [0]}
    )
    assert StateEvent(State.CLEANING) in _notified(event_bus)


def test_paused() -> None:
    event_bus, _ = _handle(
        {"battery": 75, "chargeStatus": False, "pauseSwitch": True, "workMode": "auto"}
    )
    assert StateEvent(State.PAUSED) in _notified(event_bus)


def test_idle() -> None:
    event_bus, _ = _handle(
        {"battery": 100, "chargeStatus": False, "pauseSwitch": False, "workMode": "stop"}
    )
    assert StateEvent(State.IDLE) in _notified(event_bus)


def test_fan_speed() -> None:
    for mode, expected in [
        ("quiet", FanSpeedLevel.QUIET),
        ("standard", FanSpeedLevel.NORMAL),
        ("strong", FanSpeedLevel.MAX),
        ("max", FanSpeedLevel.MAX_PLUS),
        ("auto", FanSpeedLevel.NORMAL),
    ]:
        event_bus, _ = _handle({"fanMode": mode})
        assert FanSpeedEvent(expected) in _notified(event_bus)


def test_water_mode() -> None:
    for mode, expected in [
        ("low", WaterAmount.LOW),
        ("medium", WaterAmount.MEDIUM),
        ("high", WaterAmount.HIGH),
        ("ultrahigh", WaterAmount.ULTRAHIGH),
    ]:
        event_bus, _ = _handle({"waterMode": mode})
        assert WaterAmountEvent(expected) in _notified(event_bus)


def test_mop_not_attached() -> None:
    event_bus, _ = _handle({"mopState": "none"})
    assert MopAttachedEvent(attached=False) in _notified(event_bus)


def test_mop_attached() -> None:
    event_bus, _ = _handle({"mopState": "attached"})
    assert MopAttachedEvent(attached=True) in _notified(event_bus)


def test_child_lock() -> None:
    event_bus, _ = _handle({"childLock": True})
    assert ChildLockEvent(enabled=True) in _notified(event_bus)


def test_consumables() -> None:
    event_bus, _ = _handle(
        {
            "consumables": [
                {"type": "sideBrush", "left": 6000, "total": 12000},
                {"type": "rollBrush", "left": 9000, "total": 12000},
                {"type": "filter", "left": 3000, "total": 6000},
            ]
        }
    )
    events = _notified(event_bus)
    assert LifeSpanEvent(type=LifeSpan.SIDE_BRUSH, percent=50.0, remaining=6000) in events
    assert LifeSpanEvent(type=LifeSpan.BRUSH, percent=75.0, remaining=9000) in events
    assert LifeSpanEvent(type=LifeSpan.FILTER, percent=50.0, remaining=3000) in events


def test_no_data() -> None:
    event_bus, result = _handle()
    event_bus.notify.assert_not_called()


def test_unmapped_fan_mode(caplog: pytest.LogCaptureFixture) -> None:
    event_bus, _ = _handle({"fanMode": "unknown_mode"})
    fan_events = [e for e in _notified(event_bus) if isinstance(e, FanSpeedEvent)]
    assert len(fan_events) == 0
