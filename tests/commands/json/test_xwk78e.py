from __future__ import annotations

import pytest

from deebot_client.commands.json.xwk78e import (
    GetAutoEmptyT80,
    GetTrueDetectT80,
    GetWashInfoT80,
    SetTrueDetectLevelT80,
    SetTrueDetectV2,
    SetWashInfoT80,
)
from deebot_client.events import TrueDetectEvent
from deebot_client.events.auto_empty import Frequency
from deebot_client.events.xwk78e import (
    AutoEmptyEventT80,
    TrueDetectLevel,
    TrueDetectLevelEvent,
    WashMode,
    WashModeEvent,
)
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_execute_command, assert_set_command


@pytest.mark.parametrize("enable", [False, True])
@pytest.mark.parametrize("level", list(TrueDetectLevel))
async def test_GetTrueDetectT80(enable: bool, level: TrueDetectLevel) -> None:
    json, firmware_event = get_request_json(
        get_success_body({"enable": int(enable), "level": int(level)})
    )
    await assert_command(
        GetTrueDetectT80(),
        json,
        (firmware_event, TrueDetectEvent(enable), TrueDetectLevelEvent(level)),
    )


@pytest.mark.parametrize("enable", [False, True])
@pytest.mark.parametrize("level", list(TrueDetectLevel))
async def test_SetTrueDetectV2(enable: bool, level: TrueDetectLevel) -> None:
    await assert_set_command(
        SetTrueDetectV2(enable, level),
        {"enable": int(enable), "level": int(level)},
        (TrueDetectEvent(enable), TrueDetectLevelEvent(level)),
    )


@pytest.mark.parametrize("level", list(TrueDetectLevel))
async def test_SetTrueDetectLevelT80(level: TrueDetectLevel) -> None:
    await assert_set_command(
        SetTrueDetectLevelT80(level),
        {"enable": 1, "level": int(level)},
        (TrueDetectEvent(True), TrueDetectLevelEvent(level)),
    )


@pytest.mark.parametrize("intensity", [0, 1])
async def test_GetAutoEmptyT80(intensity: int) -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {"enable": 1, "frequency": "smart", "intensity": intensity}
        )
    )
    await assert_command(
        GetAutoEmptyT80(),
        json,
        (firmware_event, AutoEmptyEventT80(True, Frequency.SMART, intensity)),
    )


@pytest.mark.parametrize("mode", list(WashMode))
async def test_SetWashInfoT80(mode: WashMode) -> None:
    await assert_execute_command(
        SetWashInfoT80(mode), {"mode": int(mode), "interval": 15}
    )


@pytest.mark.parametrize("mode", list(WashMode))
async def test_GetWashInfoT80(mode: WashMode) -> None:
    json, firmware_event = get_request_json(get_success_body({"mode": int(mode)}))
    await assert_command(
        GetWashInfoT80(), json, (firmware_event, WashModeEvent(mode))
    )
