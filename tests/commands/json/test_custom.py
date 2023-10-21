from typing import Any

import pytest

from deebot_client.commands.json.custom import CustomCommand
from deebot_client.events import CustomCommandEvent
from tests.helpers import get_message_json, get_request_json, get_success_body

from . import assert_command


@pytest.mark.parametrize(
    ("command", "json", "expected"),
    [
        (
            CustomCommand("getSleep"),
            get_request_json(get_success_body({"enable": 1})),
            CustomCommandEvent(
                "getSleep", get_message_json(get_success_body({"enable": 1}))
            ),
        ),
        (CustomCommand("getSleep"), {}, None),
    ],
)
async def test_CustomCommand(
    command: CustomCommand, json: dict[str, Any], expected: CustomCommandEvent | None
) -> None:
    await assert_command(command, json, expected)
