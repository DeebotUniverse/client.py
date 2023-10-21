import pytest

from deebot_client.commands.json import GetCleanCount, SetCleanCount
from deebot_client.events import CleanCountEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command


async def test_GetCleanCount() -> None:
    json = get_request_json(get_success_body({"count": 2}))
    await assert_command(GetCleanCount(), json, CleanCountEvent(2))


@pytest.mark.parametrize("count", [1, 2, 3])
async def test_SetCleanCount(count: int) -> None:
    args = {"count": count}
    await assert_set_command(SetCleanCount(count), args, CleanCountEvent(count))
