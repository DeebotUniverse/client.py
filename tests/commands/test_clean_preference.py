import pytest

from deebot_client.commands import GetCleanPreference, SetCleanPreference
from deebot_client.events import CleanPreferenceEvent
from tests.commands import assert_command_requested, assert_set_command
from tests.helpers import get_request_json


@pytest.mark.parametrize("value", [False, True])
def test_get_clean_preference(value: bool) -> None:
    json = get_request_json({"enable": 1 if value else 0})
    assert_command_requested(GetCleanPreference(), json, CleanPreferenceEvent(value))


@pytest.mark.parametrize("value", [False, True])
def test_set_clean_preference(value: bool) -> None:
    args = {"enable": 1 if value else 0}
    assert_set_command(SetCleanPreference(value), args, CleanPreferenceEvent(value))
