from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import (
    GetWashInfo,
)
from deebot_client.commands.json.wash_info import SetWashInfo
from deebot_client.events import WashInfoEvent, WashMode
from tests.helpers import (
    get_request_json,
    get_success_body,
    verify_DisplayNameEnum_unique,
)

from . import assert_command, assert_set_command


def test_WashInfo_unique() -> None:
    verify_DisplayNameEnum_unique(WashMode)


@pytest.mark.parametrize(
    ("json", "expected"),
    [
        (
            {"mode": 0, "interval": 12, "hot_wash_amount": 1},
            WashInfoEvent(WashMode.STANDARD, 12, 1),
        ),
        (
            {"mode": 1, "interval": 6, "hot_wash_amount": 3},
            WashInfoEvent(WashMode.HOT, 6, 3),
        ),
    ],
)
async def test_GetWashInfo(json: dict[str, Any], expected: WashInfoEvent) -> None:
    json = get_request_json(get_success_body(json))
    await assert_command(GetWashInfo(), json, expected)


@pytest.mark.parametrize(("value"), [WashMode.HOT, "hot"])
async def test_SetWashInfo_mode(value: WashMode | str) -> None:
    command = SetWashInfo(mode=value)
    args = {"mode": 1}
    await assert_set_command(command, args, WashInfoEvent(WashMode.HOT, None, None))


def test_SetWashInfo_mode_inexisting_value() -> None:
    with pytest.raises(ValueError, match="'INEXSTING' is not a valid WashMode member"):
        SetWashInfo(mode="inexsting")


@pytest.mark.parametrize(("value"), [1])
async def test_SetWashInfo_hot_wash_amount(value: int) -> None:
    command = SetWashInfo(hot_wash_amount=value)
    args = {"hot_wash_amount": value}
    await assert_set_command(command, args, WashInfoEvent(None, None, value))
