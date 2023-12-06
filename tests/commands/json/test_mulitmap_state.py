import pytest

from deebot_client.commands.json import GetMultimapState, SetMultimapState
from deebot_client.events import MultimapStateEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetMultimapState(*, value: bool) -> None:
    json = get_request_json(get_success_body({"enable": 1 if value else 0}))
    await assert_command(GetMultimapState(), json, MultimapStateEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetMultimapState(*, value: bool) -> None:
    await assert_set_enable_command(
        SetMultimapState(value), MultimapStateEvent, enabled=value
    )
