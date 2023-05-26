from typing import Any

import pytest

from deebot_client.commands import GetChargeState
from deebot_client.events import StateEvent
from tests.commands import assert_command
from tests.helpers import get_request_json


@pytest.mark.parametrize(
    "json, expected",
    [
        (get_request_json({"isCharging": 0, "mode": "slot"}), None),
    ],
)
async def test_GetChargeState(
    json: dict[str, Any], expected: StateEvent | None
) -> None:
    await assert_command(GetChargeState(), json, expected)
