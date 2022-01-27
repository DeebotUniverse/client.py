import pytest

from deebot_client.commands import GetBattery
from deebot_client.events import BatteryEvent
from tests.commands import assert_command_requested


@pytest.mark.parametrize("percentage", [0, 49, 100])
def test_get_battery_requested(percentage: int):
    data = {
        "id": "ALZf",
        "ret": "ok",
        "resp": {
            "header": {
                "pri": 1,
                "tzm": 480,
                "ts": "1304623069888",
                "ver": "0.0.1",
                "fwVer": "1.8.2",
                "hwVer": "0.1.1",
            },
            "body": {
                "code": 0,
                "msg": "ok",
                "data": {"value": percentage, "isLow": 1 if percentage < 20 else 0},
            },
        },
    }
    assert_command_requested(GetBattery(), data, BatteryEvent(percentage))
