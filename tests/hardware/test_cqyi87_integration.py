from __future__ import annotations

from typing import Any
from unittest.mock import Mock, call

import orjson
import pytest

from deebot_client.commands.json import COMMANDS
from deebot_client.commands.json.native_area import NativeCleanRoom, NativeCleanZone
from deebot_client.commands.json.native_info import GetNativeInfo
from deebot_client.commands.json.native_settings import (
    NativeSetAutoBoost,
    NativeSetChildLock,
    NativeSetContinuousCleaning,
    NativeSetDoNotDisturb,
    NativeSetVolume,
)
from deebot_client.event_bus import EventBus
from deebot_client.events import (
    CarpetAutoFanBoostEvent,
    ChildLockEvent,
    ContinuousCleaningEvent,
    DoNotDisturbEvent,
    VolumeEvent,
)
from deebot_client.hardware.cqyi87 import get_device_info
from deebot_client.message import HandlingState
from deebot_client.messages.json.native_info import OnNativeInfo
from deebot_client.models import CleanMode
from tests.commands.json import assert_command
from tests.helpers import get_request_json, get_success_body


def _native_report(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "header": {
            "pri": 3,
            "m": "cloudctl",
            "channel": "rop",
            "ver": "0.0.9",
            "fwVer": "10.0.9",
            "hwVer": "1.2.0",
            "tzm": 480,
            "ts": "1791717778000",
        },
        "body": {"data": data},
    }


def test_on_native_info_handle_five_settings() -> None:
    bus = Mock(spec_set=EventBus)
    bus.get_last_event.return_value = None
    payload = _native_report(
        {
            "childLock": False,
            "autoBoost": True,
            "breakCleanSwitch": True,
            "disturbSwitch": True,
            "volume": 10,
        }
    )
    result = OnNativeInfo.handle(bus, payload)
    assert result.state == HandlingState.SUCCESS

    bus.notify.assert_has_calls(
        [
            call(ChildLockEvent(False)),
            call(CarpetAutoFanBoostEvent(True)),
            call(ContinuousCleaningEvent(True)),
            call(DoNotDisturbEvent(True)),
            call(VolumeEvent(10, 10)),
        ],
        any_order=True,
    )


async def test_get_native_info_full_settings_response() -> None:
    body = get_success_body(
        {
            "childLock": True,
            "autoBoost": False,
            "breakCleanSwitch": False,
            "disturbSwitch": False,
            "volume": 7,
        }
    )
    json_data, firmware_event = get_request_json(body)
    await assert_command(
        GetNativeInfo(),
        json_data,
        (
            firmware_event,
            ChildLockEvent(True),
            CarpetAutoFanBoostEvent(False),
            ContinuousCleaningEvent(False),
            DoNotDisturbEvent(False),
            VolumeEvent(7, 10),
        ),
    )


def test_child_lock_failed_ack_no_state_update() -> None:
    bus = Mock(spec_set=EventBus)
    cmd = NativeSetChildLock(True)
    failed_payload = orjson.dumps({"body": {"code": 500, "msg": "Internal Error"}})
    cmd.handle_mqtt_p2p(bus, failed_payload)
    bus.notify.assert_not_called()


def test_area_factory_capability_spot_and_custom() -> None:
    capabilities = get_device_info().capabilities
    area_fn = capabilities.clean.action.area
    assert area_fn is not None

    room_cmd = area_fn(CleanMode.SPOT_AREA, [101, 102], 1)
    assert isinstance(room_cmd, NativeCleanRoom)
    assert room_cmd.NAME == "40007"
    assert room_cmd._args == {
        "cleanSwitch": True,
        "cleanMode": "area",
        "cleanValues": [101, 102],
    }

    zone_cmd = area_fn(CleanMode.CUSTOM_AREA, [-2000, 1000, 500, -500], 1)
    assert isinstance(zone_cmd, NativeCleanZone)
    assert zone_cmd.NAME == "40005"
    assert zone_cmd._args == {
        "cleanSwitch": True,
        "cleanMode": "zone",
        "cleanValues": [-200, 100, -200, -50, 50, -50, 50, 100],
    }


def test_area_factory_coordinate_ten_to_one_validation() -> None:
    capabilities = get_device_info().capabilities
    area_fn = capabilities.clean.action.area
    assert area_fn is not None

    with pytest.raises(ValueError, match="fractional centimeter"):
        area_fn(CleanMode.CUSTOM_AREA, [-2005, 1000, 500, -500], 1)

    with pytest.raises(ValueError, match="Repetition count"):
        area_fn(CleanMode.SPOT_AREA, [101], 2)

    with pytest.raises(ValueError, match="not supported"):
        area_fn(CleanMode.AUTO, [101], 1)


def test_command_registry_contains_all_seven_classes() -> None:
    expected = {
        "40007": NativeCleanRoom,
        "40005": NativeCleanZone,
        "50038": NativeSetChildLock,
        "50036": NativeSetAutoBoost,
        "50025": NativeSetContinuousCleaning,
        "50019": NativeSetDoNotDisturb,
        "50023": NativeSetVolume,
    }
    for opcode, cls in expected.items():
        assert COMMANDS[opcode] is cls
