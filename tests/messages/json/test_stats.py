from __future__ import annotations

from typing import Any

import pytest

from deebot_client.events import CleanJobStatus, ReportStatsEvent
from deebot_client.messages.json import ReportStats
from tests.messages import assert_message


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
    data = {
        "header": {
            "pri": 1,
            "tzm": 480,
            "ts": "1662017348913",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
        },
        "body": {"data": data},
    }

    assert_message(ReportStats, data, expected)
