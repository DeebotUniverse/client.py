"""Tests regarding the mower task messages."""

from __future__ import annotations

import pytest

from deebot_client.events import CleanJobStatus, ReportStatsEvent
from deebot_client.messages import get_message
from deebot_client.messages.json.mower_task import (
    OnMowAreaTaskStop,
    OnMowAutoTaskStop,
    OnMowBorderTaskStop,
    OnMowScheduleTaskStop,
)
from tests import get_static_device_info
from tests.helpers import get_message_json
from tests.messages.json import assert_message

_DEVICE_CLASS = "2px96q"


@pytest.mark.parametrize(
    ("message", "trigger", "expected_type", "expected_status"),
    [
        (OnMowAreaTaskStop, "app", "spotArea", CleanJobStatus.MANUALLY_STOPPED),
        (OnMowBorderTaskStop, "workComplete", "border", CleanJobStatus.FINISHED),
        (OnMowBorderTaskStop, "other", "border", CleanJobStatus.FINISHED_WITH_WARNINGS),
    ],
)
def test_onMowTaskStop(
    message: type[OnMowAreaTaskStop],
    trigger: str,
    expected_type: str,
    expected_status: CleanJobStatus,
) -> None:
    data, firmware_event = get_message_json(
        {
            "bid": "9961792055285349",
            "jobId": "5401792055078175",
            "mapId": "1102520059",
            "mowType": 1,
            "mowedArea": 1.6525,
            "time": 151.558899,
            "trigger": trigger,
            "workArea": 105.737503,
            "workType": 2,
        }
    )
    assert_message(
        message,
        data,
        (
            firmware_event,
            ReportStatsEvent(
                area=16525,
                time=152,
                type=expected_type,
                cleaning_id="5401792055078175",
                status=expected_status,
                content=[],
            ),
        ),
        device_class=_DEVICE_CLASS,
    )


@pytest.mark.parametrize(
    "message",
    [OnMowAreaTaskStop, OnMowAutoTaskStop, OnMowBorderTaskStop, OnMowScheduleTaskStop],
)
def test_mow_task_stop_registered(message: type[OnMowAreaTaskStop]) -> None:
    static = get_static_device_info(_DEVICE_CLASS)
    assert static
    assert get_message(message.NAME, static) is message
