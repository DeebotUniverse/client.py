import pytest

from deebot_client.events import BatteryEvent
from deebot_client.messages.xml.battery import OnBattery
from tests.messages import assert_message


@pytest.mark.parametrize("percentage", [0, 49, 100])
def test_onBattery(percentage: int) -> None:
    data = {
        "header": {
            "pri": 1,
            "tzm": 480,
            "ts": "1304637391896",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
        },
        "body": {
            "ret": "ok",
            "resp": f"<ctl ret='ok'><battery power='{percentage}'/></ctl>",
        },
    }

    assert_message(OnBattery, data, BatteryEvent(percentage))
