import pytest

from deebot_client.commands import GetCarpetAutoFanBoost, SetCarpetAutoFanBoost
from deebot_client.events import CarpetAutoFanBoostEvent
from tests.commands import assert_command_requested, assert_set_command
from tests.helpers import get_request_json


@pytest.mark.parametrize("value", [False, True])
def test_get_carpet_auto_fan_boost_requested(value: bool) -> None:
    json = get_request_json({"enable": 1 if value else 0})
    assert_command_requested(
        GetCarpetAutoFanBoost(), json, CarpetAutoFanBoostEvent(value)
    )


@pytest.mark.parametrize("value", [False, True])
def test_set_carpet_auto_fan_boost(value: bool) -> None:
    args = {"enable": 1 if value else 0}
    assert_set_command(
        SetCarpetAutoFanBoost(value), args, CarpetAutoFanBoostEvent(value)
    )
