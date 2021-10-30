from deebot_client.commands import FanSpeedLevel
from tests.helpers import verify_DisplayNameEnum_unique


def test_FanSpeedLevel_unique():
    verify_DisplayNameEnum_unique(FanSpeedLevel)
