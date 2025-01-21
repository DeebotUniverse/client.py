from __future__ import annotations

from typing import Any

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.json import PlaySound
from deebot_client.message import HandlingState
from tests.helpers import get_request_json, get_success_body

from . import assert_command


@pytest.mark.parametrize(
    ("json", "command_result"),
    [
        (get_request_json(get_success_body()), CommandResult.success()),
        (get_request_json({"code": -1, "msg": "failed", "data": ""}), CommandResult(HandlingState.FAILED)),
    ],
)
async def test_play_sound(json: dict[str, Any], command_result: CommandResult) -> None:
    await assert_command(PlaySound(), json, None, command_result=command_result)
