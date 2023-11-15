import pytest

from deebot_client.commands.json import GetOta, SetOta
from deebot_client.events import OtaEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetOta(value: bool) -> None:
    json = get_request_json(get_success_body({"autoSwitch": 1 if value else 0}))
    await assert_command(GetOta(), json, OtaEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetOta(value: bool) -> None:
    args = {"autoSwitch": value}
    await assert_set_command(SetOta(value), args, OtaEvent(value))
