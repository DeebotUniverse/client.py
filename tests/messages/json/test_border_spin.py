from __future__ import annotations

from typing import Any

import pytest

from deebot_client.events import BorderSpinEvent, FirmwareEvent
from deebot_client.messages.json.border_spin import OnBorderSpin
from tests.messages.json import assert_message


@pytest.mark.parametrize("enable", [True, False])
def test_onBorderSpin(*, enable: bool) -> None:
    data: dict[str, Any] = {
        "header": {
            "pri": 1,
            "tzm": 60,
            "ts": "1734719921057",
            "ver": "0.0.1",
            "fwVer": "1.30.0",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {"data": {"enable": int(enable)}},
    }

    assert_message(
        OnBorderSpin,
        data,
        (FirmwareEvent("1.30.0"), BorderSpinEvent(enable)),
    )
