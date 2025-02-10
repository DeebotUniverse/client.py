from __future__ import annotations

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.xml.clean import CleanArea
from deebot_client.message import HandlingState
from deebot_client.models import CleanMode
from tests.commands import assert_command

from . import get_request_xml


@pytest.mark.parametrize(
    ("command", "command_result"),
    [
        (CleanArea(CleanMode.SPOT_AREA, "4", 1), HandlingState.SUCCESS),
    ],
)
async def test_CleanArea(command: CleanArea, command_result: HandlingState) -> None:
    json = get_request_xml("<ctl ret='ok'/>")
    await assert_command(
        command, json, None, command_result=CommandResult(command_result)
    )
