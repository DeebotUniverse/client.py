from __future__ import annotations

import pytest

from deebot_client.commands.json import GetCutDirection, SetCutDirection
from deebot_client.events import CutDirectionEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command


async def test_GetCutDirection() -> None:
    json = get_request_json(get_success_body({"angle": 90}))
    await assert_command(GetCutDirection(), json, CutDirectionEvent(90))


@pytest.mark.parametrize("angle", [1, 45, 90])
async def test_SetCutDirection(angle: int) -> None:
    args = {"angle": angle}
    await assert_set_command(SetCutDirection(angle), args, CutDirectionEvent(angle))
