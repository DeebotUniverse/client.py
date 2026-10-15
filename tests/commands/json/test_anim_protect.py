"""Tests regarding animal protection and rain delay commands."""

from __future__ import annotations

from deebot_client.commands.json import (
    GetAnimProtect,
    GetRainDelay,
    SetAnimProtect,
    SetRainDelay,
)
from deebot_client.events.mower import AnimalProtectionEvent, RainDelayEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command


async def test_GetAnimProtect() -> None:
    json, firmware_event = get_request_json(
        get_success_body({"enable": 1, "start": "19:0", "end": "8:0"})
    )
    await assert_command(
        GetAnimProtect(),
        json,
        (
            firmware_event,
            AnimalProtectionEvent(enabled=True, start="19:00", end="08:00"),
        ),
    )


async def test_SetAnimProtect() -> None:
    await assert_set_command(
        SetAnimProtect(enabled=False, start="19:00", end="08:00"),
        {"enable": 0, "start": "19:0", "end": "8:0"},
        AnimalProtectionEvent(enabled=False, start="19:00", end="08:00"),
    )


async def test_GetRainDelay() -> None:
    json, firmware_event = get_request_json(
        get_success_body({"enable": 1, "delay": 300})
    )
    await assert_command(
        GetRainDelay(),
        json,
        (firmware_event, RainDelayEvent(enabled=True, delay=300)),
    )


async def test_SetRainDelay() -> None:
    await assert_set_command(
        SetRainDelay(enabled=False, delay=300),
        {"enable": 0, "delay": 300},
        RainDelayEvent(enabled=False, delay=300),
    )
