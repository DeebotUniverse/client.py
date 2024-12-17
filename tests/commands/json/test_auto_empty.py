"""Auto empty tests."""

from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json.auto_empty import GetAutoEmpty, SetAutoEmpty
from deebot_client.events.auto_empty import AutoEmptyEvent, Frequency
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
            AutoEmptyEvent(True, Frequency.MIN_10),
        ),
        (
            {"enable": 1, "frequency": "15"},
            AutoEmptyEvent(True, Frequency.MIN_15),
        ),
        (
            {"enable": 1, "frequency": "25"},
            AutoEmptyEvent(True, Frequency.MIN_25),
        ),
        (
            {"enable": 0, "frequency": "auto"},
            AutoEmptyEvent(False, Frequency.AUTO),
        ),
        (
            {"enable": 1, "frequency": "auto"},
            AutoEmptyEvent(True, Frequency.AUTO),
        ),
        (
            {"enable": 1, "frequency": "smart"},
            AutoEmptyEvent(True, Frequency.SMART),
        ),
    ],
)
async def test_GetAutoEmpty(json: dict[str, Any], expected: AutoEmptyEvent) -> None:
    """Test GetAutoEmpty."""
    json = get_request_json(get_success_body(json))
    await assert_command(GetAutoEmpty(), json, expected)


@pytest.mark.parametrize(
    ("enabled", "frequency", "args"),
    [
        (
            True,
            "min_10",
            {"enable": 1, "frequency": "10"},
        ),
        (
            True,
            Frequency.MIN_10,
            {"enable": 1, "frequency": "10"},
        ),
        (
            True,
            "smart",
            {"enable": 1, "frequency": "smart"},
        ),
        (
            False,
            "min_10",
            {"enable": 0, "frequency": "10"},
        ),
        (
            False,
            Frequency.MIN_10,
            {"enable": 0, "frequency": "10"},
        ),
        (
            False,
            "smart",
            {"enable": 0, "frequency": "smart"},
        ),
        (
            None,
            "min_10",
            {"frequency": "10"},
        ),
        (
            None,
            Frequency.MIN_10,
            {"frequency": "10"},
        ),
        (
            None,
            "smart",
            {"frequency": "smart"},
        ),
        (
            True,
            None,
            {"enable": 1},
        ),
        (
            False,
            None,
            {"enable": 0},
        ),
    ],
)
async def test_SetAutoEmpty(
    enabled: bool,
    frequency: str | Frequency | None,
    args: dict[str, Any],
) -> None:
    """Test SetAutoEmpty."""
    command = SetAutoEmpty(enabled, frequency)
    await assert_execute_command(command, args)
