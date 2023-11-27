from typing import Any

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.events import CustomCommandEvent
from deebot_client.message import HandlingState
from tests.helpers import get_message_json, get_request_json, get_success_body

from . import assert_command


@pytest.mark.parametrize(
    ("command", "json", "expected", "command_result"),
    [
        (
            CustomCommand("getSleep"),
            get_request_json(get_success_body({"enable": 1})),
            CustomCommandEvent(
                "getSleep", get_message_json(get_success_body({"enable": 1}))
            ),
            CommandResult.success(),
        ),
        (CustomCommand("getSleep"), {}, None, CommandResult(HandlingState.FAILED)),
    ],
)
async def test_CustomCommand(
    command: CustomCommand,
    json: dict[str, Any],
    expected: CustomCommandEvent | None,
    command_result: CommandResult,
) -> None:
    await assert_command(command, json, expected, command_result)
