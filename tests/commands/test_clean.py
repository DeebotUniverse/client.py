from typing import Any

import pytest

from deebot_client.commands import GetCleanInfo
from deebot_client.events import StateEvent
from deebot_client.models import VacuumState
from tests.commands import assert_command
from tests.helpers import get_request_json


@pytest.mark.parametrize(
    "json, expected",
    [
        (
            get_request_json({"trigger": "none", "state": "idle"}),
            StateEvent(VacuumState.IDLE),
        ),
    ],
)
async def test_GetCleanInfo(json: dict[str, Any], expected: StateEvent) -> None:
    await assert_command(GetCleanInfo(), json, expected)
