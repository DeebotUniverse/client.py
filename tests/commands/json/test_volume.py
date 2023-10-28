import pytest

from deebot_client.commands.json import GetVolume, SetVolume
from deebot_client.events import VolumeEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command


async def test_GetVolume() -> None:
    json = get_request_json(get_success_body({"volume": 2, "total": 10}))
    await assert_command(GetVolume(), json, VolumeEvent(2, 10))


@pytest.mark.parametrize("level", [0, 2, 10])
async def test_SetCleanCount(level: int) -> None:
    args = {"volume": level}
    await assert_set_command(SetVolume(level), args, VolumeEvent(level, None))
