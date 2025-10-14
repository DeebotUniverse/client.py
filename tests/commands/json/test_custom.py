from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json.custom import CustomCommand
from deebot_client.events import CustomCommandEvent
from deebot_client.message import HandlingResult, HandlingState
from tests.helpers import get_message_json, get_request_json, get_success_body

from . import assert_command


@pytest.mark.parametrize(
    ("command", "json", "expected", "handling_result"),
    [
        (
            CustomCommand("getSleep"),
            get_request_json(get_success_body({"enable": 1}))[0],
            CustomCommandEvent(
                "getSleep", get_message_json(get_success_body({"enable": 1}))[0]
            ),
            HandlingResult.success(),
        ),
        (CustomCommand("getSleep"), {}, None, HandlingResult(HandlingState.FAILED)),
    ],
)
async def test_CustomCommand(
    command: CustomCommand,
    json: dict[str, Any],
    expected: CustomCommandEvent | None,
    handling_result: HandlingResult,
) -> None:
    await assert_command(command, json, expected, handling_result=handling_result)
