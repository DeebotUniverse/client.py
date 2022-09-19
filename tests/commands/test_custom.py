from typing import Any

import pytest

from deebot_client.commands.custom import CustomCommand
from deebot_client.events import CustomCommandEvent
from tests.commands import assert_command_requested
from tests.helpers import get_message_json, get_request_json


@pytest.mark.parametrize(
    "command, json, expected",
    [
        (
            CustomCommand("getSleep"),
            get_request_json({"enable": 1}),
            CustomCommandEvent("getSleep", get_message_json({"enable": 1})),
        ),
        (CustomCommand("getSleep"), {}, None),
    ],
)
async def test_CustomCommand(
    command: CustomCommand, json: dict[str, Any], expected: CustomCommandEvent | None
) -> None:
    await assert_command_requested(command, json, expected)
