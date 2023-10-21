import pytest

from deebot_client.commands.json import GetAdvancedMode, SetAdvancedMode
from deebot_client.events import AdvancedModeEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetAdvancedMode(value: bool) -> None:
    json = get_request_json(get_success_body({"enable": 1 if value else 0}))
    await assert_command(GetAdvancedMode(), json, AdvancedModeEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetAdvancedMode(value: bool) -> None:
    await assert_set_enable_command(SetAdvancedMode(value), value, AdvancedModeEvent)
