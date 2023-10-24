from typing import Any

import pytest

from deebot_client.commands.json import GetChargeState
from deebot_client.events import StateEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command


@pytest.mark.parametrize(
    ("json", "expected"),
    [
        (get_request_json(get_success_body({"isCharging": 0, "mode": "slot"})), None),
    ],
)
async def test_GetChargeState(
    json: dict[str, Any], expected: StateEvent | None
) -> None:
    await assert_command(GetChargeState(), json, expected)
