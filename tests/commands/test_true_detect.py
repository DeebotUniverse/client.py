import pytest

from deebot_client.commands import GetTrueDetect, SetTrueDetect
from deebot_client.events import TrueDetectEvent
from tests.commands import assert_command_requested, assert_set_command
from tests.helpers import get_request_json


@pytest.mark.parametrize("value", [False, True])
def test_get_true_detect(value: bool) -> None:
    json = get_request_json({"enable": 1 if value else 0})
    assert_command_requested(GetTrueDetect(), json, TrueDetectEvent(value))


@pytest.mark.parametrize("value", [False, True])
def test_set_true_detect(value: bool) -> None:
    args = {"enable": 1 if value else 0}
    assert_set_command(SetTrueDetect(value), args, TrueDetectEvent(value))
