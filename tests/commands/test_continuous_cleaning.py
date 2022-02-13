import pytest

from deebot_client.commands import GetContinuousCleaning, SetContinuousCleaning
from deebot_client.events import ContinuousCleaningEvent
from tests.commands import assert_command_requested, assert_set_command
from tests.helpers import get_request_json


@pytest.mark.parametrize("value", [False, True])
def test_get_continuous_cleaning_requested(value: bool):
    json = get_request_json({"enable": 1 if value else 0})
    assert_command_requested(
        GetContinuousCleaning(), json, ContinuousCleaningEvent(value)
    )


@pytest.mark.parametrize("value", [False, True])
def test_set_continuous_cleaning(value: bool):
    args = {"enable": 1 if value else 0}
    assert_set_command(
        SetContinuousCleaning(value), args, ContinuousCleaningEvent(value)
    )
