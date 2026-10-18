from __future__ import annotations

from typing import Any

import pytest

from deebot_client.events import FirmwareEvent, OtaEvent
from deebot_client.messages.json.ota import OnOta
from tests.messages.json import assert_message


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param(
            {
                "autoSwitch": 1,
                "supportAuto": 1,
                "cver": "1.8.0",
                "status": "upgrading",
                "progress": 45,
            },
            OtaEvent(
                support_auto=True,
                auto_enabled=True,
                version="1.8.0",
                status="upgrading",
                progress=45,
            ),
            id="full",
        ),
        pytest.param(
            {"autoSwitch": 0, "supportAuto": 1, "ver": "1.7.2"},
            OtaEvent(support_auto=True, auto_enabled=False, version="1.7.2"),
            id="without_status_and_progress",
        ),
    ],
)
def test_onOta(data: dict[str, Any], expected: OtaEvent) -> None:
    message: dict[str, Any] = {
        "header": {
            "pri": 1,
            "tzm": 60,
            "ts": "1734719921057",
            "ver": "0.0.1",
            "fwVer": "1.30.0",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {"data": data},
    }

    assert_message(OnOta, message, (FirmwareEvent("1.30.0"), expected))
