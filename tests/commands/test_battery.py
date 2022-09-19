import pytest

from deebot_client.commands import GetBattery
from deebot_client.events import BatteryEvent
from tests.commands import assert_command_requested
from tests.helpers import get_request_json


@pytest.mark.parametrize("percentage", [0, 49, 100])
async def test_get_battery_requested(percentage: int) -> None:
    json = get_request_json({"value": percentage, "isLow": 1 if percentage < 20 else 0})
    await assert_command_requested(GetBattery(), json, BatteryEvent(percentage))
