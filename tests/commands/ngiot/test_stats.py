from __future__ import annotations

from unittest.mock import Mock

from deebot_client.commands.ngiot.stats import GetReportStats, GetStats, GetTotalStats
from deebot_client.event_bus import EventBus
from deebot_client.events import CleanJobStatus, ReportStatsEvent, StatsEvent, TotalStatsEvent
from deebot_client.message import HandlingResult, HandlingState


def test_get_stats_converts_minutes_to_seconds() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetStats._handle_body_data_dict(
        event_bus,
        {"cleanArea": "25", "cleanTime": "12", "workMode": "smart"},
    )

    assert result == HandlingResult(HandlingState.SUCCESS)
    event_bus.notify.assert_called_once_with(
        StatsEvent(area=25, time=720, type="smart")
    )


def test_get_report_stats_extracts_cleaning_id() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetReportStats._handle_body_data_dict(
        event_bus,
        {
            "cleanArea": 15,
            "cleanTime": 7,
            "workMode": "area",
            "cleanLogReport": {"cid": "job-123"},
        },
    )

    assert result == HandlingResult(HandlingState.SUCCESS)
    event_bus.notify.assert_called_once_with(
        ReportStatsEvent(
            area=15,
            time=420,
            type="area",
            cleaning_id="job-123",
            status=CleanJobStatus.NO_STATUS,
            content=[],
        )
    )


def test_get_total_stats_uses_total_fields_and_fallbacks() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetTotalStats._handle_body_data_dict(
        event_bus,
        {
            "cleanAreaTotal": "101",
            "cleanTime": 8,
            "cleanCount": "9",
        },
    )

    assert result == HandlingResult(HandlingState.SUCCESS)
    event_bus.notify.assert_called_once_with(
        TotalStatsEvent(area=101, time=480, cleanings=9)
    )
