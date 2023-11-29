import pytest

from deebot_client.commands.json import GetCleanPreference, SetCleanPreference
from deebot_client.events import CleanPreferenceEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetCleanPreference(*, value: bool) -> None:
    json = get_request_json(get_success_body({"enable": 1 if value else 0}))
    await assert_command(GetCleanPreference(), json, CleanPreferenceEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetCleanPreference(*, value: bool) -> None:
    await assert_set_enable_command(
        SetCleanPreference(value), CleanPreferenceEvent, enabled=value
    )
