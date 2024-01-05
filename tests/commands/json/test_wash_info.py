from typing import Any

import pytest

from deebot_client.commands.json import (
    GetWashInfo,
)
from deebot_client.events import WashInfoEvent, WashMode
from tests.helpers import (
    get_request_json,
    get_success_body,
    verify_DisplayNameEnum_unique,
)

from . import assert_command


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
