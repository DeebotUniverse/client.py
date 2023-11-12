from typing import Any

import pytest

from deebot_client.commands.json import GetWorkMode, SetWorkMode
from deebot_client.events import WorkMode, WorkModeEvent
from tests.helpers import (
    get_request_json,
    get_success_body,
    verify_DisplayNameEnum_unique,
)

from . import assert_command, assert_set_command


def test_WorkMode_unique() -> None:
    verify_DisplayNameEnum_unique(WorkMode)


@pytest.mark.parametrize(
    ("json", "expected"),
    [
        ({"mode": 0}, WorkModeEvent(WorkMode.VACUUM_AND_MOP)),
        ({"mode": 1}, WorkModeEvent(WorkMode.VACUUM)),
        ({"mode": 2}, WorkModeEvent(WorkMode.MOP)),
        ({"mode": 3}, WorkModeEvent(WorkMode.MOP_AFTER_VACUUM)),
    ],
)
async def test_GetWaterInfo(json: dict[str, Any], expected: WorkModeEvent) -> None:
    json = get_request_json(get_success_body(json))
    await assert_command(GetWorkMode(), json, expected)


@pytest.mark.parametrize(("value"), [WorkMode.MOP_AFTER_VACUUM, "mop_after_vacuum"])
async def test_SetWaterInfo(value: WorkMode | str) -> None:
    command = SetWorkMode(value)
    args = {"mode": 3}
    await assert_set_command(command, args, WorkModeEvent(WorkMode.MOP_AFTER_VACUUM))


def test_SetWaterInfo_inexisting_value() -> None:
    with pytest.raises(ValueError, match="'INEXSTING' is not a valid WorkMode member"):
        SetWorkMode("inexsting")
