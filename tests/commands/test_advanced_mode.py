import pytest

from deebot_client.commands import GetAdvancedMode, SetAdvancedMode
from deebot_client.events import AdvancedModeEvent
from tests.commands import assert_command, assert_set_command
from tests.helpers import get_request_json


@pytest.mark.parametrize("value", [False, True])
async def test_GetAdvancedMode(value: bool) -> None:
    json = get_request_json({"enable": 1 if value else 0})
    await assert_command(GetAdvancedMode(), json, AdvancedModeEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetAdvancedMode(value: bool) -> None:
    args = {"enable": 1 if value else 0}
    await assert_set_command(SetAdvancedMode(value), args, AdvancedModeEvent(value))
