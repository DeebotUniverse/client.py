from deebot_client.commands.json import GetTotalStats
from deebot_client.events import TotalStatsEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command


async def test_GetTotalStats() -> None:
    area = 123
    time = 167
    count = 56
    json = get_request_json(
        get_success_body({"area": area, "time": time * 60, "count": count})
    )
    await assert_command(GetTotalStats(), json, TotalStatsEvent(area, time, count))
