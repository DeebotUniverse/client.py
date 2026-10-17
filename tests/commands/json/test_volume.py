from __future__ import annotations

import pytest

from deebot_client.commands.json import GetVolume, SetFallVolume, SetVolume
from deebot_client.events import FallVolumeEvent, VolumeEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command


async def test_GetVolume() -> None:
    json, firmware_event = get_request_json(
        get_success_body({"volume": 2, "total": 10})
    )
    await assert_command(GetVolume(), json, (firmware_event, VolumeEvent(2, 10)))


async def test_GetMowerVolume() -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {"total": 10, "volume": 5, "fallVolume": 2, "searchVolume": 10}
        )
    )
    await assert_command(
        GetVolume(),
        json,
        (firmware_event, VolumeEvent(5, 10), FallVolumeEvent(2, 10)),
    )


@pytest.mark.parametrize("level", [0, 2, 10])
async def test_SetVolume(level: int) -> None:
    args = {"volume": level}
    await assert_set_command(SetVolume(level), args, VolumeEvent(level, None))


async def test_SetMowerSystemVolume() -> None:
    args = {"type": "sys", "total": 10, "volume": 6}
    await assert_set_command(
        SetVolume(6, channel="sys", total=10), args, VolumeEvent(6, 10)
    )


@pytest.mark.parametrize("level", [2, 6, 10])
async def test_SetFallVolume(level: int) -> None:
    args = {"type": "fall", "total": 10, "volume": level}
    await assert_set_command(SetFallVolume(level), args, FallVolumeEvent(level, 10))
