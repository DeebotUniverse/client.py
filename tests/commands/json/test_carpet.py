import pytest

from deebot_client.commands.json import GetCarpetAutoFanBoost, SetCarpetAutoFanBoost
from deebot_client.events import CarpetAutoFanBoostEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetCarpetAutoFanBoost(value: bool) -> None:
    json = get_request_json(get_success_body({"enable": 1 if value else 0}))
    await assert_command(GetCarpetAutoFanBoost(), json, CarpetAutoFanBoostEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetCarpetAutoFanBoost(value: bool) -> None:
    await assert_set_enable_command(
        SetCarpetAutoFanBoost(value), value, CarpetAutoFanBoostEvent
    )
