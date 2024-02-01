import pytest

from deebot_client.commands.json import GetSweepMode, SetSweepMode
from deebot_client.events import SweepModeEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command


@pytest.mark.parametrize("type", [False, True])
async def test_GetSweepMode(type: bool) -> None:
    json = get_request_json(get_success_body({"type": 1 if type else 0}))
    await assert_command(GetSweepMode(), json, SweepModeEvent(type))


@pytest.mark.parametrize("type", [False, True])
async def test_SetSweepMode(type: bool) -> None:
    args = {"type": 1 if type else 0}
    await assert_set_command(SetSweepMode(type), args, SweepModeEvent(type))
