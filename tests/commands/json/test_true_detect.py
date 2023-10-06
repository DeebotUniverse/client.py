import pytest

from deebot_client.commands.json import GetTrueDetect, SetTrueDetect
from deebot_client.events import TrueDetectEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetTrueDetect(value: bool) -> None:
    json = get_request_json(get_success_body({"enable": 1 if value else 0}))
    await assert_command(GetTrueDetect(), json, TrueDetectEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetTrueDetect(value: bool) -> None:
    args = {"enable": 1 if value else 0}
    await assert_set_command(SetTrueDetect(value), args, TrueDetectEvent(value))
