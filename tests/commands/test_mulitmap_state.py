import pytest

from deebot_client.commands import GetMultimapState, SetMultimapState
from deebot_client.events import MultimapStateEvent
from tests.commands import assert_command, assert_set_command
from tests.helpers import get_request_json


@pytest.mark.parametrize("value", [False, True])
async def test_GetMultimapState(value: bool) -> None:
    json = get_request_json({"enable": 1 if value else 0})
    await assert_command(GetMultimapState(), json, MultimapStateEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetMultimapState(value: bool) -> None:
    args = {"enable": 1 if value else 0}
    await assert_set_command(SetMultimapState(value), args, MultimapStateEvent(value))
