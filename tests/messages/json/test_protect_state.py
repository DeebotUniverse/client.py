from __future__ import annotations

from typing import Any

import pytest

from deebot_client.events import FirmwareEvent, ProtectStateEvent
from deebot_client.messages.json import OnProtectState
from tests.messages.json import assert_message


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (
            {
                "isAnimProtect": 0,
                "isRainProtect": 1,
                "isRainDelay": 0,
                "isEStop": 0,
                "isLocked": 0,
                "isPinCode": 0,
                "isPrepareDataSuccess": 1,
            },
            ProtectStateEvent(
                is_anim_protect=False,
                is_rain_protect=True,
                is_rain_delay=False,
                is_e_stop=False,
                is_locked=False,
                is_pin_code=False,
                is_prepare_data_success=True,
            ),
        ),
        (
            {
                "isAnimProtect": 0,
                "isRainProtect": 0,
                "isRainDelay": 0,
                "isEStop": 0,
                "isLocked": 0,
                "isPinCode": 0,
                "isPrepareDataSuccess": 0,
            },
            ProtectStateEvent(
                is_anim_protect=False,
                is_rain_protect=False,
                is_rain_delay=False,
                is_e_stop=False,
                is_locked=False,
                is_pin_code=False,
                is_prepare_data_success=False,
            ),
        ),
        (
            {
                "isAnimProtect": 1,
                "isRainProtect": 0,
                "isRainDelay": 1,
                "isEStop": 0,
                "isLocked": 1,
                "isPinCode": 0,
                "isPrepareDataSuccess": 1,
            },
            ProtectStateEvent(
                is_anim_protect=True,
                is_rain_protect=False,
                is_rain_delay=True,
                is_e_stop=False,
                is_locked=True,
                is_pin_code=False,
                is_prepare_data_success=True,
            ),
        ),
    ],
    ids=["observed-rain", "all-zero", "bool-conversion"],
)
def test_on_protect_state(data: dict[str, Any], expected: ProtectStateEvent) -> None:
    payload = {
        "header": {"fwVer": "1.13.10"},
        "body": {"data": data, "code": 0, "msg": "ok"},
    }

    assert_message(OnProtectState, payload, (FirmwareEvent("1.13.10"), expected))
