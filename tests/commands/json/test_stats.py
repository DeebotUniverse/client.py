from __future__ import annotations

from deebot_client.commands.json import GetStats
from deebot_client.events import StatsEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command


async def test_GetStats() -> None:
    json, firmware_event = get_request_json(
        get_success_body({"area": 2889500, "time": 11269, "mowedArea": 1005475})
    )
    await assert_command(
        GetStats(),
        json,
        (
            firmware_event,
            StatsEvent(area=2889500, time=11269, type=None, mowed_area=1005475),
        ),
    )
