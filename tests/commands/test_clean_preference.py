import pytest

from deebot_client.commands import GetCleanPreference, SetCleanPreference
from deebot_client.events import CleanPreferenceEvent
from tests.commands import assert_command, assert_set_command
from tests.helpers import get_request_json


@pytest.mark.parametrize("value", [False, True])
async def test_GetCleanPreference(value: bool) -> None:
    json = get_request_json({"enable": 1 if value else 0})
    await assert_command(GetCleanPreference(), json, CleanPreferenceEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetCleanPreference(value: bool) -> None:
    args = {"enable": 1 if value else 0}
    await assert_set_command(
        SetCleanPreference(value), args, CleanPreferenceEvent(value)
    )
