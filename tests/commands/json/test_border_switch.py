"""Tests regarding border switch commands."""

from __future__ import annotations

import pytest

from deebot_client.commands.json import GetBorderSwitch, SetBorderSwitch
from deebot_client.commands.json.border_switch import SetBorderSwitchMode
from deebot_client.events import BorderSwitchEvent
from deebot_client.events.mower import BorderSwitchMode, BorderSwitchModeEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetBorderSwitch(*, value: bool) -> None:
    """Testing get border switch."""
    json, firmware_event = get_request_json(
        get_success_body({"enable": 1 if value else 0})
    )
    await assert_command(
        GetBorderSwitch(), json, (firmware_event, BorderSwitchEvent(value))
    )


@pytest.mark.parametrize("value", [False, True])
async def test_SetBorderSwitch(*, value: bool) -> None:
    """Testing set border switch."""
    await assert_set_command(
        SetBorderSwitch(value),
        {"enable": 1 if value else 0},
        BorderSwitchEvent(value),
    )


@pytest.mark.parametrize("mode", list(BorderSwitchMode))
async def test_GetBorderSwitch_mode(mode: BorderSwitchMode) -> None:
    """Testing get border switch with mode."""
    json, firmware_event = get_request_json(
        get_success_body({"enable": 1, "mode": mode.value})
    )
    await assert_command(
        GetBorderSwitch(),
        json,
        (firmware_event, BorderSwitchEvent(True), BorderSwitchModeEvent(mode)),
    )


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (BorderSwitchMode.CROSS_BOUNDARY, BorderSwitchMode.CROSS_BOUNDARY),
        ("along_border", BorderSwitchMode.ALONG_BORDER),
    ],
)
async def test_SetBorderSwitchMode(
    mode: BorderSwitchMode | str, expected: BorderSwitchMode
) -> None:
    """Testing set border switch mode."""
    await assert_set_command(
        SetBorderSwitchMode(mode),
        {"enable": 1, "mode": expected.value},
        (BorderSwitchEvent(True), BorderSwitchModeEvent(expected)),
    )
