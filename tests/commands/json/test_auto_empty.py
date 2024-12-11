"""Auto empty tests."""

from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json.auto_empty import GetAutoEmpty, SetAutoEmpty
from deebot_client.events.auto_empty import Event, Frequency
from tests.helpers import (
    get_request_json,
    get_success_body,
)

from . import assert_command, assert_execute_command


@pytest.mark.parametrize(
    ("json", "expected"),
    [
        (
            {"enable": 1, "frequency": "10"},
            Event(Frequency.MIN_10),
        ),
        (
            {"enable": 1, "frequency": "15"},
            Event(Frequency.MIN_15),
        ),
        (
            {"enable": 1, "frequency": "25"},
            Event(Frequency.MIN_25),
        ),
        (
            {"enable": 0, "frequency": "auto"},
            Event(Frequency.OFF),
        ),
        (
            {"enable": 1, "frequency": "auto"},
            Event(Frequency.AUTO),
        ),
        (
            {"enable": 1, "frequency": "smart"},
            Event(Frequency.SMART),
        ),
    ],
)
async def test_GetAutoEmpty(json: dict[str, Any], expected: Event) -> None:
    """Test GetAutoEmpty."""
    json = get_request_json(get_success_body(json))
    await assert_command(GetAutoEmpty(), json, expected)


@pytest.mark.parametrize(
    ("frequency", "args"),
    [
        (
            "min_10",
            {"enable": 1, "frequency": "10"},
        ),
        (
            Frequency.MIN_10,
            {"enable": 1, "frequency": "10"},
        ),
        (
            "smart",
            {"enable": 1, "frequency": "smart"},
        ),
        (
            Frequency.OFF,
            {"enable": 0},
        ),
        (
            "off",
            {"enable": 0},
        ),
    ],
)
async def test_SetAutoEmpty(
    frequency: str | Frequency,
    args: dict[str, Any],
) -> None:
    """Test SetAutoEmpty."""
    command = SetAutoEmpty(frequency)
    await assert_execute_command(command, args)
