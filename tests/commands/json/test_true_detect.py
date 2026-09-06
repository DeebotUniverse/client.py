from __future__ import annotations

import pytest

from deebot_client.commands.json import GetTrueDetect, SetTrueDetect
from deebot_client.commands.json.xwk78e import SetTrueDetectV2
from deebot_client.events import TrueDetectEvent
from deebot_client.events.xwk78e import TrueDetectLevel, TrueDetectLevelEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetTrueDetect(*, value: bool) -> None:
    json, firmware_event = get_request_json(
        get_success_body({"enable": 1 if value else 0})
    )
    await assert_command(
        GetTrueDetect(), json, (firmware_event, TrueDetectEvent(value))
    )


@pytest.mark.parametrize("value", [False, True])
async def test_SetTrueDetect(*, value: bool) -> None:
    await assert_set_enable_command(
        SetTrueDetect(value), TrueDetectEvent, enabled=value
    )


@pytest.mark.parametrize("value", [False, True])
async def test_SetTrueDetectV2_default_level(*, value: bool) -> None:
    command = SetTrueDetectV2(value)
    await assert_set_command(
        command,
        {"enable": 1 if value else 0, "level": 1},
        (TrueDetectEvent(value), TrueDetectLevelEvent(TrueDetectLevel.STANDARD)),
    )


@pytest.mark.parametrize(
    ("value", "level"),
    [(False, 0), (True, 0), (True, 1)],
)
async def test_SetTrueDetectV2(*, value: bool, level: int) -> None:
    command = SetTrueDetectV2(value, level)
    await assert_set_command(
        command,
        {"enable": 1 if value else 0, "level": level},
        (TrueDetectEvent(value), TrueDetectLevelEvent(TrueDetectLevel(level))),
    )
