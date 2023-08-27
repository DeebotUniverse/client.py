import pytest

from deebot_client.commands.json import GetContinuousCleaning, SetContinuousCleaning
from deebot_client.events import ContinuousCleaningEvent
from tests.helpers import get_request_json

from . import assert_command, assert_set_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetContinuousCleaning(value: bool) -> None:
    json = get_request_json({"enable": 1 if value else 0})
    await assert_command(GetContinuousCleaning(), json, ContinuousCleaningEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetContinuousCleaning(value: bool) -> None:
    args = {"enable": 1 if value else 0}
    await assert_set_command(
        SetContinuousCleaning(value), args, ContinuousCleaningEvent(value)
    )
