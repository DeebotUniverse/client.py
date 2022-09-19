import pytest

from deebot_client.commands import GetAdvancedMode, SetAdvancedMode
from deebot_client.events import AdvancedModeEvent
from tests.commands import assert_command_requested, assert_set_command
from tests.helpers import get_request_json


@pytest.mark.parametrize("value", [False, True])
async def test_get_advanced_mode_requested(value: bool) -> None:
    json = get_request_json({"enable": 1 if value else 0})
    await assert_command_requested(GetAdvancedMode(), json, AdvancedModeEvent(value))


@pytest.mark.parametrize("value", [False, True])
def test_set_advanced_mode(value: bool) -> None:
    args = {"enable": 1 if value else 0}
    assert_set_command(SetAdvancedMode(value), args, AdvancedModeEvent(value))
