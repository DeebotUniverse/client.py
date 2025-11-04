from __future__ import annotations

from typing import Any

import pytest

from deebot_client.events import (
    CleanJobStatus,
    FirmwareEvent,
    ReportStatsEvent,
    StatsEvent,
)
from deebot_client.messages.json import OnStats, ReportStats
from tests.messages.json import assert_message


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
@pytest.mark.benchmark
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

    assert_message(ReportStats, data, (FirmwareEvent("1.8.2"), expected))


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (
            {
                "area": 2,
                "time": 89,
                "cid": "2002066096",
                "start": "1744009746",
                "type": "auto",
                "enablePowerMop": 1,
                "powerMopType": 2,
                "aiopen": 1,
                "aitypes": [9],
                "avoidCount": 1,
            },
            StatsEvent(
                area=2,
                time=89,
                type="auto",
            ),
        ),
        (
            {
                "area": 50,
                "time": 56289,
                "cid": "2002066096",
                "start": "1744009746",
                "type": "auto",
                "enablePowerMop": 1,
                "powerMopType": 2,
                "aiopen": 1,
                "aitypes": [9],
                "avoidCount": 1,
            },
            StatsEvent(
                area=50,
                time=56289,
                type="auto",
            ),
        ),
        (
            {"mowid": "0", "time": 11269, "area": 2889500, "mowedArea": 1005475},
            StatsEvent(
                area=2889500,
                time=11269,
                type=None,
            ),
        ),
    ],
)
@pytest.mark.benchmark
def test_onStats(data: dict[str, Any], expected: StatsEvent) -> None:
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

    assert_message(OnStats, data, (FirmwareEvent("1.8.2"), expected))
