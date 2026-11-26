from __future__ import annotations

import re

import pytest

from deebot_client.command import GetCommand
from deebot_client.commands.json import GetBattery
from deebot_client.commands.json.common import JsonGetCommand
from deebot_client.commands.json.native_info import GetNativeInfo
from deebot_client.events import BatteryEvent, ErrorEvent, StateEvent
from deebot_client.messages.json.native_info import NativeInfoEvent
from deebot_client.models import State
from tests.helpers import get_request_json, get_success_body

from . import assert_command


def test_native_wire_header_exact() -> None:
    payload = GetNativeInfo(["battery"])._get_payload()
    assert isinstance(payload, dict)
    header = payload["header"]
    assert header["pri"] == 3
    assert header["m"] == "cloudctl"
    assert header["channel"] == "rop"
    assert header["ver"] == "0.0.1"
    assert header["tzm"] == 480
    assert isinstance(header["ts"], str)
    assert re.fullmatch(r"\d{13}", header["ts"]) is not None
    assert payload["body"] == {"data": {"fields": ["battery"]}}


def test_native_default_fields() -> None:
    command = GetNativeInfo()
    assert command._args == {
        "fields": [
            "status",
            "pauseSwitch",
            "chargeStatus",
            "battery",
            "fanMode",
            "waterMode",
            "mopState",
            "consumables",
            "deviceInfo",
            "error",
            "cleanArea",
            "cleanTime",
            "childLock",
            "autoBoost",
            "breakCleanSwitch",
            "disturbSwitch",
            "volume",
        ]
    }


async def test_get_native_info_through_transport() -> None:
    body = get_success_body(
        {"status": "smartClean", "pauseSwitch": False, "battery": 100}
    )
    json, firmware_event = get_request_json(body)
    await assert_command(
        GetNativeInfo(["status", "pauseSwitch", "battery"]),
        json,
        (
            firmware_event,
            BatteryEvent(100),
            StateEvent(State.CLEANING),
            NativeInfoEvent(
                status="smartClean", charge_status=None, pause_switch=False
            ),
        ),
    )


@pytest.mark.parametrize(
    ("code", "description"),
    [(102, "Robot is lifted"), (111, "Bumper is stuck"), (0, "No error")],
)
async def test_get_native_error_description_through_transport(
    code: int, description: str
) -> None:
    body = get_success_body({"error": [code]})
    payload, firmware_event = get_request_json(body)
    await assert_command(
        GetNativeInfo(["error"]),
        payload,
        (firmware_event, ErrorEvent(code, description)),
    )


def test_legacy_getter_header_unaffected() -> None:
    payload = GetBattery()._get_payload()
    assert isinstance(payload, dict)
    assert payload["header"]["pri"] == "1"
    assert payload["header"]["ver"] == "0.0.50"
    assert payload["header"]["tzm"] == 480


def test_get_command_semantics() -> None:
    assert isinstance(GetNativeInfo(), GetCommand)
    assert isinstance(GetNativeInfo(), JsonGetCommand)
    assert GetNativeInfo()._is_available_check is False
    assert GetNativeInfo(is_available_check=True)._is_available_check is True
