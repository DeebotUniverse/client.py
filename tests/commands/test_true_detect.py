import pytest

from deebot_client.commands import GetTrueDetect, SetTrueDetect
from deebot_client.events import TrueDetectEvent
from tests.commands import assert_command, assert_set_command
from tests.helpers import get_request_json


@pytest.mark.parametrize("value", [False, True])
async def test_GetTrueDetect(value: bool) -> None:
    json = get_request_json({"enable": 1 if value else 0})
    await assert_command(GetTrueDetect(), json, TrueDetectEvent(value))


@pytest.mark.parametrize("value", [False, True])
def test_SetTrueDetect(value: bool) -> None:
    args = {"enable": 1 if value else 0}
    assert_set_command(SetTrueDetect(value), args, TrueDetectEvent(value))
