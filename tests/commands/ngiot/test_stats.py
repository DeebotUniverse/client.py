from __future__ import annotations

from typing import cast
from unittest.mock import Mock

from deebot_client.commands.ngiot.stats import GetReportStats, GetStats, GetTotalStats
from deebot_client.event_bus import EventBus
from deebot_client.events import (
    CleanJobStatus,
    ReportStatsEvent,
    StatsEvent,
    TotalStatsEvent,
)
from deebot_client.message import HandlingState


def test_get_stats_notifies_stats_event() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetStats.handle(
        cast("EventBus", event_bus),
        {
            "body": {
                "data": {
                    "cleanArea": 12,
                    "cleanTime": 7,
                    "workMode": "smart",
                }
            }
        },
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(
        StatsEvent(area=12, time=420, type="smart")
    )


def test_get_report_stats_notifies_report_stats_event() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetReportStats.handle(
        cast("EventBus", event_bus),
        {
            "body": {
                "data": {
                    "cleanArea": 12,
                    "cleanTime": 7,
                    "workMode": "smart",
                    "cleanLogReport": {"cid": "060"},
                }
            }
        },
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(
        ReportStatsEvent(
            area=12,
            time=420,
            type="smart",
            cleaning_id="060",
            status=CleanJobStatus.NO_STATUS,
            content=[],
        )
    )


def test_get_total_stats_notifies_total_stats_event() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetTotalStats.handle(
        cast("EventBus", event_bus),
        {
            "body": {
                "data": {
                    "cleanAreaTotal": 80,
                    "cleanTimeTotal": 25,
                    "cleanCountTotal": 4,
                }
            }
        },
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(
        TotalStatsEvent(area=80, time=1500, cleanings=4)
    )
