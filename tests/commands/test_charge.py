from typing import Any

import pytest

from deebot_client.commands import Charge
from deebot_client.events import StatusEvent
from deebot_client.models import VacuumState
from tests.commands import assert_command_requested
from tests.helpers import get_request_json


def prepare_json_docked_test():
    json = get_request_json(None)
    json["resp"]["body"]["code"] = 30007
    return json


@pytest.mark.parametrize(
    "json, expected",
    [
        (get_request_json(None), StatusEvent(True, VacuumState.RETURNING)),
        (prepare_json_docked_test(), StatusEvent(True, VacuumState.DOCKED)),
    ],
)
def test_charge(json: dict[str, Any], expected: StatusEvent):
    assert_command_requested(Charge(), json, expected)
