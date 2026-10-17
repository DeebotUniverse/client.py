from __future__ import annotations

import pytest

from deebot_client.events import FirmwareEvent, RainDelayEvent
from deebot_client.messages.json import OnRainDelay
from tests.messages.json import assert_message


@pytest.mark.parametrize(
    ("enable", "delay", "enabled"),
    [(0, 180, False), (1, 0, True), (1, 30, True), (1, 300, True)],
)
def test_on_rain_delay(enable: int, delay: int, enabled: bool) -> None:
    data = {
        "header": {"fwVer": "1.13.10"},
        "body": {"data": {"enable": enable, "delay": delay}},
    }

    assert_message(
        OnRainDelay,
        data,
        (FirmwareEvent("1.13.10"), RainDelayEvent(enabled=enabled, delay=delay)),
    )
