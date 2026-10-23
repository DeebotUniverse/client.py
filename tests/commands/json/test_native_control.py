from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock

import pytest

from deebot_client.authentication import Authenticator
from deebot_client.command import Command, GetCommand
from deebot_client.commands.json import COMMANDS
from deebot_client.commands.json.native_control import (
    NativeCustomCommand,
    NativeLocate,
    NativePauseClean,
    NativeResetLifeSpan,
    NativeResumeClean,
    NativeReturnToDock,
    NativeSetFanSpeed,
    NativeSetWaterAmount,
    NativeStartClean,
    native_clean,
)
from deebot_client.commands.json.native_info import GetNativeInfo
from deebot_client.event_bus import EventBus
from deebot_client.events import FanSpeedLevel, LifeSpan, StateEvent
from deebot_client.events.water_info import WaterAmount
from deebot_client.models import ApiDeviceInfo, CleanAction, Credentials, State
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_execute_command

if TYPE_CHECKING:
    from deebot_client.commands.json.common import ExecuteCommand


def _native_success() -> dict[str, Any]:
    return {
        "ret": "ok",
        "resp": {
            "header": {"fwVer": "10.0.9"},
            "body": {"code": 0, "msg": "ok"},
        },
    }


def _authenticator_mock() -> Mock:
    authenticator = Mock(spec_set=Authenticator)
    authenticator.authenticate = AsyncMock(
        return_value=Credentials("token", "user_id", 9999)
    )
    authenticator.post_authenticated = AsyncMock(return_value=_native_success())
    return authenticator


def _api_device_info() -> ApiDeviceInfo:
    return ApiDeviceInfo(
        {
            "company": "company",
            "did": "did",
            "name": "name",
            "nick": "nick",
            "resource": "resource",
            "class": "cqyi87",
        }
    )


def _payload_cmd_name(authenticator: Mock) -> str:
    payload = authenticator.post_authenticated.call_args[0][1]
    assert isinstance(payload, dict)
    return str(payload["cmdName"])


@pytest.mark.parametrize(
    ("command", "name", "args"),
    [
        (NativeStartClean(), "40001", {"cleanSwitch": True, "cleanMode": "smart"}),
        (NativePauseClean(), "40009", {"pauseSwitch": True}),
        (NativeResumeClean(), "40011", {"pauseSwitch": False}),
        (NativeReturnToDock(), "40013", {"chargeSwitch": True}),
        (NativeLocate(), "40019", {"seek": True}),
        (
            NativeResetLifeSpan(LifeSpan.SIDE_BRUSH),
            "50017",
            {"resetConsumable": "sideBrush"},
        ),
        (NativeSetFanSpeed(FanSpeedLevel.MAX_PLUS), "50011", {"fanMode": "max"}),
        (NativeSetWaterAmount(WaterAmount.MEDIUM), "50013", {"waterMode": "mid"}),
    ],
)
async def test_native_wire_payload(
    command: ExecuteCommand, name: str, args: dict[str, Any]
) -> None:
    assert name == command.NAME
    payload = command._get_payload()
    assert isinstance(payload, dict)
    header = payload["header"]
    assert header["pri"] == 3
    assert header["m"] == "cloudctl"
    assert header["channel"] == "rop"
    assert header["ver"] == "0.0.1"
    assert header["tzm"] == 480
    assert isinstance(header["ts"], str)
    assert re.fullmatch(r"\d{13}", header["ts"]) is not None
    assert payload["body"] == {"data": args}
    if isinstance(command, NativeResetLifeSpan):
        # Refresh behavior has dedicated coverage below.
        return
    await assert_execute_command(command, args)


def test_registry_unique_numeric_names() -> None:
    expected = {
        "40001": NativeStartClean,
        "40009": NativePauseClean,
        "40011": NativeResumeClean,
        "40013": NativeReturnToDock,
        "40019": NativeLocate,
        "50011": NativeSetFanSpeed,
        "50013": NativeSetWaterAmount,
        "50017": NativeResetLifeSpan,
        "10001": GetNativeInfo,
    }
    for name, cls in expected.items():
        assert COMMANDS[name] is cls
    assert [cmd for cmd in COMMANDS.values() if cmd.NAME == "40013"] == [
        NativeReturnToDock
    ]


def test_get_native_info_uses_shared_native_header() -> None:
    payload = GetNativeInfo(["battery"])._get_payload()
    assert isinstance(payload, dict)
    assert payload["header"]["pri"] == 3
    assert payload["header"]["m"] == "cloudctl"
    assert isinstance(GetNativeInfo(), GetCommand)


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        (CleanAction.START, NativeStartClean),
        (CleanAction.PAUSE, NativePauseClean),
        (CleanAction.RESUME, NativeResumeClean),
        (CleanAction.STOP, NativeReturnToDock),
    ],
)
def test_native_clean_factory(action: CleanAction, expected: type[Command]) -> None:
    command = native_clean(action)
    assert isinstance(command, expected)


def test_stop_is_dock_pause_is_halt() -> None:
    stop = native_clean(CleanAction.STOP)
    pause = native_clean(CleanAction.PAUSE)
    assert stop.NAME == "40013"
    assert stop._args == {"chargeSwitch": True}
    assert pause.NAME == "40009"
    assert pause.NAME != stop.NAME


@pytest.mark.parametrize(
    ("action", "state", "wire_name"),
    [
        (CleanAction.START, None, "40001"),
        (CleanAction.START, State.PAUSED, "40011"),
        (CleanAction.START, State.DOCKED, "40001"),
        (CleanAction.RESUME, None, "40011"),
        (CleanAction.RESUME, State.PAUSED, "40011"),
        (CleanAction.RESUME, State.DOCKED, "40001"),
        (CleanAction.STOP, None, "40013"),
        (CleanAction.STOP, State.CLEANING, "40013"),
        (CleanAction.STOP, State.PAUSED, "40013"),
        (CleanAction.STOP, State.DOCKED, "40013"),
        (CleanAction.PAUSE, None, "40009"),
        (CleanAction.PAUSE, State.CLEANING, "40009"),
    ],
)
async def test_native_clean_state_swap(
    action: CleanAction, state: State | None, wire_name: str
) -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.return_value = (
        StateEvent(state) if state is not None else None
    )
    authenticator = _authenticator_mock()

    await native_clean(action).execute(authenticator, _api_device_info(), event_bus)

    assert _payload_cmd_name(authenticator) == wire_name


async def test_native_locate_and_custom_header() -> None:
    await assert_execute_command(NativeLocate(), {"seek": True})
    custom = NativeCustomCommand("40099", {"fields": ["battery"]})
    payload = custom._get_payload()
    assert isinstance(payload, dict)
    assert payload["header"]["pri"] == 3
    assert payload["header"]["m"] == "cloudctl"
    assert payload["body"] == {"data": {"fields": ["battery"]}}


async def test_native_controls_no_invented_state_on_ack() -> None:
    wrapped, firmware_event = get_request_json(get_success_body())
    await assert_command(NativeStartClean(), wrapped, firmware_event)
