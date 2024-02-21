from __future__ import annotations

from typing import Any

import pytest

from deebot_client.events import CleanJobStatus, ReportStatsEvent, StatsEvent
from deebot_client.messages.json import OnStats, ReportStats
from tests.helpers import get_message_json, get_success_body
from tests.messages import assert_message


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (
            {"area": 35, "time": 2004, "cid": "111", "type": "auto"},
            StatsEvent(area=35, time=2004, type="auto"),
        ),
        (
            {"time": 2004, "cid": "111", "type": "auto"},
            StatsEvent(area=None, time=2004, type="auto"),
        ),
        (
            {"cid": "111"},
            StatsEvent(area=None, time=None, type=None),
        ),
    ],
)
def test_OnStats(data: dict[str, Any], expected: StatsEvent) -> None:
    json = get_message_json(get_success_body(data))
    assert_message(OnStats, json, expected)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (
            {
                "cid": "391593403",
                "type": "spotArea",
                "stop": 1,
                "mapCount": 17,
                "area": 24,
                "time": 1736,
                "start": "1662015610",
                "content": "0,4,2,12",
                "stopReason": 3,
            },
            ReportStatsEvent(
                24,
                1736,
                "spotArea",
                "391593403",
                CleanJobStatus.FINISHED_WITH_WARNINGS,
                [0, 4, 2, 12],
            ),
        ),
        (
            {"cid": "1897815235", "type": "spotArea", "stop": 0},
            ReportStatsEvent(
                None, None, "spotArea", "1897815235", CleanJobStatus.CLEANING, []
            ),
        ),
        (
            {"cid": "1897815236", "type": "spotArea"},
            ReportStatsEvent(
                None, None, "spotArea", "1897815236", CleanJobStatus.NO_STATUS, []
            ),
        ),
    ],
)
def test_ReportStats(data: dict[str, Any], expected: ReportStatsEvent) -> None:
    json = get_message_json(get_success_body(data))
    assert_message(ReportStats, json, expected)
