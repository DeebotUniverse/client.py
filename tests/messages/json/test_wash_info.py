from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.events import FirmwareEvent
from deebot_client.events.mop_auto_wash_frequency import MopAutoWashFrequencyEvent
from deebot_client.events.wash_info import (
    MopAutoWashMode,
    MopAutoWashModeEvent,
    MopWashMode,
    MopWashModeEvent,
)
from deebot_client.messages.json.wash_info import OnWashInfo
from tests.messages.json import assert_message

if TYPE_CHECKING:
    from deebot_client.events import Event


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (
            # T90 PRO (guaexd / twunby), firmware 1.103.0
            {
                "amount": 1,
                "dryMop": 0,
                "duration": 60,
                "interval": 10,
                "mode": 3,
                "wiseMode": 0,
            },
            (
                MopAutoWashFrequencyEvent(10),
                MopWashModeEvent(MopWashMode.INTELLIGENT_TEMPERATURE),
                MopAutoWashModeEvent(MopAutoWashMode.BY_TIME),
            ),
        ),
        ({"mode": 1}, (MopWashModeEvent(MopWashMode.STANDARD),)),
        ({"wiseMode": 1}, (MopAutoWashModeEvent(MopAutoWashMode.BY_ROOM),)),
    ],
)
def test_onWashInfo(data: dict[str, Any], expected: tuple[Event, ...]) -> None:
    payload = {
        "header": {
            "pri": 1,
            "tzm": 600,
            "ts": "1792589829925",
            "ver": "0.0.1",
            "fwVer": "1.103.0",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {"data": data},
    }
    assert_message(
        OnWashInfo,
        payload,
        (FirmwareEvent("1.103.0"), *expected),
        device_class="twunby",
    )
