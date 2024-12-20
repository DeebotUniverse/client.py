from __future__ import annotations

from typing import Any

import pytest

from deebot_client.events import auto_empty
from deebot_client.messages.json.auto_empty import OnAutoEmpty
from tests.messages import assert_message


@pytest.mark.parametrize(
    ("frequency", "expected_freq"),
    [
        (None, None),
        ("10", auto_empty.Frequency.MIN_10),
        ("auto", auto_empty.Frequency.AUTO),
        ("smart", auto_empty.Frequency.SMART),
    ],
)
@pytest.mark.parametrize("enable", [True, False])
def test_onAutoEmpty(
    frequency: str | None, expected_freq: auto_empty.Frequency | None, enable: bool
) -> None:
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
        "body": {"data": {"status": 0, "enable": int(enable)}},
    }
    if frequency is not None:
        data["body"]["data"]["frequency"] = frequency

    assert_message(OnAutoEmpty, data, auto_empty.AutoEmptyEvent(enable, expected_freq))
