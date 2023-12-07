from typing import Any

import pytest

from deebot_client.commands.json import GetAutoEmpty, SetAutoEmpty
from deebot_client.events import AutoEmptyMode, AutoEmptyModeEvent
from tests.helpers import (
    get_request_json,
    get_success_body,
    verify_DisplayNameStrEnum_unique,
)

from . import assert_command, assert_set_command


def test_WorkMode_unique() -> None:
    verify_DisplayNameStrEnum_unique(AutoEmptyMode)


@pytest.mark.parametrize(
    ("json", "expected"),
    [
        (
            {"enable": 1, "frequency": "10"},
            AutoEmptyModeEvent(enable=True, mode=AutoEmptyMode.MODE_10),
        ),
        (
            {"enable": 1, "frequency": "15"},
            AutoEmptyModeEvent(enable=True, mode=AutoEmptyMode.MODE_15),
        ),
        (
            {"enable": 1, "frequency": "25"},
            AutoEmptyModeEvent(enable=True, mode=AutoEmptyMode.MODE_25),
        ),
        (
            {"enable": 0, "frequency": "25"},
            AutoEmptyModeEvent(enable=False, mode=AutoEmptyMode.MODE_25),
        ),
        (
            {"enable": 1, "frequency": "auto"},
            AutoEmptyModeEvent(enable=True, mode=AutoEmptyMode.MODE_AUTO),
        ),
        (
            {"enable": 1, "frequency": "smart"},
            AutoEmptyModeEvent(enable=True, mode=AutoEmptyMode.MODE_SMART),
        ),
    ],
)
async def test_GetAutoEmpty(json: dict[str, Any], expected: AutoEmptyModeEvent) -> None:
    json = get_request_json(get_success_body(json))
    await assert_command(GetAutoEmpty(), json, expected)


@pytest.mark.parametrize(
    ("value", "args", "expected"),
    [
        (
            (True, AutoEmptyMode.MODE_10),
            {"enable": 1, "frequency": "10"},
            AutoEmptyModeEvent(enable=True, mode=AutoEmptyMode.MODE_10),
        ),
        (
            (True, "mode_smart"),
            {"enable": 1, "frequency": "smart"},
            AutoEmptyModeEvent(enable=True, mode=AutoEmptyMode.MODE_SMART),
        ),
        # NOTE: this test is also working, as 'enable' will set auto to 'true' if not provided
        # as 'enable' is required when set a 'frequency'
        (
            (None, AutoEmptyMode.MODE_25),
            {"enable": 1, "frequency": "25"},
            AutoEmptyModeEvent(enable=True, mode=AutoEmptyMode.MODE_25),
        ),
        # NOTE: it should be possible to only send 'True' for turn on without 'frequency',
        # but not sure how to implement the test correct
        (
            (True, AutoEmptyMode.MODE_AUTO),
            {"enable": 1, "frequency": "auto"},
            AutoEmptyModeEvent(enable=True, mode=AutoEmptyMode.MODE_AUTO),
        ),
        # NOTE: it should be possible to only send 'False' for turn off without 'frequency',
        # but not sure how to implement the test correct
        (
            (False, AutoEmptyMode.MODE_AUTO),
            {"enable": 0, "frequency": "auto"},
            AutoEmptyModeEvent(enable=False, mode=AutoEmptyMode.MODE_AUTO),
        ),
    ],
)
async def test_SetAutoEmpty(
    value: tuple[bool | None, AutoEmptyMode | str | None],
    args: dict[str, Any],
    expected: AutoEmptyModeEvent,
) -> None:
    command = SetAutoEmpty()
    if value[0] is None and value[1] is not None:
        command = SetAutoEmpty(frequency=value[1])
    elif value[1] is None and value[0] is not None:
        command = SetAutoEmpty(enable=value[0])
    elif value[0] is not None and value[1] is not None:
        command = SetAutoEmpty(value[0], value[1])

    await assert_set_command(command, args, expected)


@pytest.mark.parametrize(
    ("value", "args", "expected"),
    [
        (
            (None, AutoEmptyMode.MODE_AUTO),
            {"enable": 0, "frequency": "auto"},
            AutoEmptyModeEvent(enable=False, mode=AutoEmptyMode.MODE_AUTO),
        ),
        (
            (None, None),
            {"enable": 0, "frequency": "auto"},
            AutoEmptyModeEvent(enable=False, mode=AutoEmptyMode.MODE_AUTO),
        ),
    ],
)
async def test_SetAutoEmptyFail(
    value: tuple[bool | None, AutoEmptyMode | str | None],
    args: dict[str, Any],
    expected: AutoEmptyModeEvent,
) -> None:
    command = SetAutoEmpty()
    if value[0] is None and value[1] is not None:
        command = SetAutoEmpty(frequency=value[1])
    elif value[1] is None and value[0] is not None:
        command = SetAutoEmpty(enable=value[0])
    elif value[0] is not None and value[1] is not None:
        command = SetAutoEmpty(value[0], value[1])

    with pytest.raises(AssertionError):
        await assert_set_command(command, args, expected)
