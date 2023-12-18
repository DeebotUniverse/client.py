from typing import Any

import pytest

from deebot_client.commands.json import GetWashInterval, SetWashInterval
from deebot_client.events import WashIntervalEvent
from tests.helpers import (
    get_request_json,
    get_success_body,
)

from . import assert_command, assert_set_command


@pytest.mark.parametrize(
    ("json", "expected"),
    [
        ({"interval": 6}, WashIntervalEvent(6)),
        ({"interval": 10}, WashIntervalEvent(10)),
    ],
)
async def test_GetPadsCleaningInterval(
    json: dict[str, Any], expected: WashIntervalEvent
) -> None:
    json = get_request_json(get_success_body(json))
    await assert_command(GetWashInterval(), json, expected)


async def test_SetWashInterval() -> None:
    command = SetWashInterval(60)
    args = {"interval": 60}
    await assert_set_command(command, args, WashIntervalEvent(60))


def test_SetWashInterval_invalid_value() -> None:
    with pytest.raises(ValueError, match="'interval' must be positive"):
        SetWashInterval(0)
