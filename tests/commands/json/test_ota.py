from __future__ import annotations

import pytest

from deebot_client.commands.json import GetOta, SetOta
from deebot_client.events import OtaEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command


@pytest.mark.parametrize(
    ("auto_enabled", "support_auto"),
    [
        (False, True),
        (True, True),
        (False, False),
    ],
)
async def test_GetOta(*, auto_enabled: bool, support_auto: bool) -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "autoSwitch": 1 if auto_enabled else 0,
                "supportAuto": 1 if support_auto else 0,
                "ver": "1.7.2",
                "status": "idle",
                "progress": 0,
            }
        )
    )
    await assert_command(
        GetOta(),
        json,
        (
            firmware_event,
            OtaEvent(
                auto_enabled=auto_enabled,
                support_auto=support_auto,
                version="1.7.2",
                status="idle",
                progress=0,
            ),
        ),
    )


@pytest.mark.parametrize(
    ("data", "version"),
    [
        pytest.param({"ver": "1.7.2"}, "1.7.2", id="ver"),
        pytest.param({"cver": "1.8.0"}, "1.8.0", id="cver"),
        pytest.param({"cver": "1.8.0", "ver": "1.7.2"}, "1.8.0", id="cver_and_ver"),
        pytest.param({"cver": "", "ver": "1.7.2"}, "1.7.2", id="empty_cver"),
        pytest.param({}, None, id="no_version"),
    ],
)
async def test_GetOta_version(data: dict[str, str], version: str | None) -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {"autoSwitch": 0, "supportAuto": 1, "status": "idle", "progress": 0} | data
        )
    )
    await assert_command(
        GetOta(),
        json,
        (
            firmware_event,
            OtaEvent(
                auto_enabled=False,
                support_auto=True,
                version=version,
                status="idle",
                progress=0,
            ),
        ),
    )


@pytest.mark.parametrize("auto_enabled", [False, True])
async def test_SetOta(*, auto_enabled: bool) -> None:
    args = {"autoSwitch": auto_enabled}
    await assert_set_command(
        SetOta(auto_enabled),
        args,
        OtaEvent(auto_enabled=auto_enabled, support_auto=True),
    )
