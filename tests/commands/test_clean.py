from typing import Any

import pytest

from deebot_client.commands import GetCleanInfo
from deebot_client.events import StatusEvent
from deebot_client.models import VacuumState
from tests.commands import assert_command_requested
from tests.helpers import get_request_json


@pytest.mark.parametrize(
    "json, expected",
    [
        (
            get_request_json({"trigger": "none", "state": "idle"}),
            StatusEvent(True, VacuumState.IDLE),
        ),
    ],
)
async def test_GetCleanInfo(json: dict[str, Any], expected: StatusEvent) -> None:
    await assert_command_requested(GetCleanInfo(), json, expected)
