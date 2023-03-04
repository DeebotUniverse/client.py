import pytest

from deebot_client.commands import GetCarpetAutoFanBoost, SetCarpetAutoFanBoost
from deebot_client.events import CarpetAutoFanBoostEvent
from tests.commands import assert_command, assert_set_command
from tests.helpers import get_request_json


@pytest.mark.parametrize("value", [False, True])
async def test_GetCarpetAutoFanBoost(value: bool) -> None:
    json = get_request_json({"enable": 1 if value else 0})
    await assert_command(GetCarpetAutoFanBoost(), json, CarpetAutoFanBoostEvent(value))


@pytest.mark.parametrize("value", [False, True])
def test_SetCarpetAutoFanBoost(value: bool) -> None:
    args = {"enable": 1 if value else 0}
    assert_set_command(
        SetCarpetAutoFanBoost(value), args, CarpetAutoFanBoostEvent(value)
    )
