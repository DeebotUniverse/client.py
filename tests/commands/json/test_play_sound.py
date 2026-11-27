"""Tests regarding the play sound commands."""

from __future__ import annotations

from deebot_client.commands.json import PlaySound
from deebot_client.commands.json.play_sound import PlayAlarmSound

from . import assert_execute_command


async def test_PlaySound() -> None:
    await assert_execute_command(PlaySound(), {"count": 1, "sid": 30})
    await assert_execute_command(PlayAlarmSound(), {"count": 1, "sid": 51})
