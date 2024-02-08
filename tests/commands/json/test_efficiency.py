from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import GetEfficiencyMode, SetEfficiencyMode
from deebot_client.events import EfficiencyMode, EfficiencyModeEvent
from tests.helpers import (
    get_request_json,
    get_success_body,
    verify_DisplayNameEnum_unique,
)

from . import assert_command, assert_set_command


def test_WorkMode_unique() -> None:
    verify_DisplayNameEnum_unique(EfficiencyMode)


@pytest.mark.parametrize(
    ("json", "expected"),
    [
        ({"efficiency": 0}, EfficiencyModeEvent(EfficiencyMode.STANDART_MODE)),
        ({"efficiency": 1}, EfficiencyModeEvent(EfficiencyMode.ENERGY_EFFICIENT_MODE)),
    ],
)
async def test_GetEfficiencyMode(
    json: dict[str, Any], expected: EfficiencyModeEvent
) -> None:
    json = get_request_json(get_success_body(json))
    await assert_command(GetEfficiencyMode(), json, expected)


@pytest.mark.parametrize(("value"), [EfficiencyMode.STANDART_MODE, "standart_mode"])
async def test_SetEfficiencyMode(value: EfficiencyMode | str) -> None:
    command = SetEfficiencyMode(value)
    args = {"efficiency": 0}
    await assert_set_command(
        command, args, EfficiencyModeEvent(EfficiencyMode.STANDART_MODE)
    )
