from __future__ import annotations

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.xml import PlaySound
from deebot_client.message import HandlingState
from tests.commands import assert_command

from . import get_request_xml


@pytest.mark.parametrize(
    ("xml_response", "command_result"),
    [
        ("<ctl ret='ok'/>", HandlingState.SUCCESS),
        ("<ctl ret='fail'/>", HandlingState.FAILED),
    ],
)
async def test_play_sound(xml_response: str, command_result: HandlingState) -> None:
    json = get_request_xml(xml_response)
    await assert_command(
        PlaySound(), json, None, command_result=CommandResult(command_result)
    )
