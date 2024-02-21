from __future__ import annotations

import pytest

from deebot_client.events import BatteryEvent
from deebot_client.messages.json import OnBattery
from tests.helpers import get_message_json, get_success_body
from tests.messages import assert_message


@pytest.mark.parametrize("percentage", [0, 49, 100])
def test_OnBattery(percentage: int) -> None:
    data = get_message_json(
        get_success_body({"value": percentage, "isLow": 1 if percentage < 20 else 0})
    )
    assert_message(OnBattery, data, BatteryEvent(percentage))
