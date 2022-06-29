from typing import Any

import pytest

from deebot_client.commands import GetChargeState
from deebot_client.events import StatusEvent
from tests.commands import assert_command_requested
from tests.helpers import get_request_json


@pytest.mark.parametrize(
    "json, expected",
    [
        (get_request_json({"isCharging": 0, "mode": "slot"}), None),
    ],
)
def test_GetChargeState(json: dict[str, Any], expected: StatusEvent | None) -> None:
    assert_command_requested(GetChargeState(), json, expected)
