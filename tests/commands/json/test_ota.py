from __future__ import annotations

import pytest

from deebot_client.commands.json import GetOta, SetOta
from deebot_client.events import OtaEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command


@pytest.mark.parametrize(
    ("auto_switch", "support_auto"),
    [
        (False, True),
        (True, False),
    ],
)
async def test_GetOta(auto_switch: bool, support_auto: bool) -> None:  # noqa: FBT001
    json = get_request_json(
        get_success_body(
            {
                "autoSwitch": 1 if auto_switch else 0,
                "supportAuto": 1 if support_auto else 0,
            }
        )
    )
    await assert_command(
        GetOta(), json, OtaEvent(auto_switch, support_auto, None, None, None)
    )


@pytest.mark.parametrize("auto_switch", [False, True])
async def test_SetOta(auto_switch: bool) -> None:  # noqa: FBT001
    args = {"autoSwitch": auto_switch}
    await assert_set_command(
        SetOta(auto_switch), args, OtaEvent(auto_switch, None, None, None, None)
    )
