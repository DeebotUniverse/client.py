"""Native duration units and partial updates."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from deebot_client.event_bus import EventBus
from deebot_client.events import ReportStatsEvent, StatsEvent
from deebot_client.hardware.cqyi87 import get_device_info
from deebot_client.messages.json.native_info import OnNativeInfo
from deebot_client.messages.json.native_stats import OnNativeCleanInfo


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"cleanArea": 10, "cleanTime": 3}, StatsEvent(10, 180, None)),
        ({"cleanTime": 3}, StatsEvent(None, 180, None)),
        ({"cleanArea": 10}, StatsEvent(10, None, None)),
        ({"cleanArea": 0, "cleanTime": 0}, StatsEvent(0, 0, None)),
    ],
)
def test_native_stats_minutes_become_seconds(
    data: dict[str, int], expected: StatsEvent
) -> None:
    bus = EventBus(AsyncMock(), get_device_info().capabilities)
    OnNativeInfo.handle(bus, {"body": {"data": data}})
    assert bus.get_last_event(StatsEvent) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"cleanTime": 4}, StatsEvent(10, 240, None)),
        ({"cleanArea": 12}, StatsEvent(12, 180, None)),
        ({"cleanTime": -1}, StatsEvent(10, 180, None)),
        ({"cleanTime": True}, StatsEvent(10, 180, None)),
        ({"cleanTime": "4"}, StatsEvent(10, 180, None)),
    ],
)
def test_partial_native_stats_preserve_other_fields(
    data: dict[str, int | str], expected: StatsEvent
) -> None:
    bus = EventBus(AsyncMock(), get_device_info().capabilities)
    OnNativeInfo.handle(bus, {"body": {"data": {"cleanArea": 10, "cleanTime": 3}}})
    OnNativeInfo.handle(bus, {"body": {"data": data}})
    assert bus.get_last_event(StatsEvent) == expected


def test_native_completion_duration_is_already_seconds() -> None:
    bus = EventBus(AsyncMock(), get_device_info().capabilities)
    OnNativeInfo.handle(bus, {"body": {"data": {"cleanArea": 10, "cleanTime": 3}}})
    OnNativeCleanInfo.handle(bus, {"body": {"cleanTime": 181, "cleanArea": 999}})
    assert bus.get_last_event(StatsEvent) == StatsEvent(10, 181, None)
    assert bus.get_last_event(ReportStatsEvent) is None


def test_native_completion_does_not_change_legacy_stats(event_bus: EventBus) -> None:
    event_bus.notify(StatsEvent(10, 180, None))
    OnNativeCleanInfo.handle(event_bus, {"body": {"cleanTime": 999}})
    assert event_bus.get_last_event(StatsEvent) == StatsEvent(10, 180, None)
