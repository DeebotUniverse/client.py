from __future__ import annotations

import time
from typing import Any
from unittest.mock import Mock

import orjson
import pytest

from deebot_client.commands.json.native_settings import (
    NativeSetAutoBoost,
    NativeSetChildLock,
    NativeSetContinuousCleaning,
    NativeSetDoNotDisturb,
    NativeSetVolume,
)
from deebot_client.event_bus import EventBus
from deebot_client.exceptions import DeebotError


def _verify_header(payload: dict[str, Any] | list[Any]) -> None:
    assert isinstance(payload, dict)
    assert "header" in payload
    header = payload["header"]
    assert header["pri"] == 3
    assert header["m"] == "cloudctl"
    assert header["channel"] == "rop"
    assert header["ver"] == "0.0.1"
    assert header["tzm"] == 480
    assert isinstance(header["ts"], str)
    ts = int(header["ts"])
    now_ms = int(time.time() * 1000)
    assert abs(now_ms - ts) < 10000


@pytest.mark.parametrize("enable", [True, False])
def test_native_child_lock_command(*, enable: bool) -> None:
    cmd = NativeSetChildLock(enable)
    assert cmd.NAME == "50038"
    assert cmd._args == {"childLock": enable}
    payload = cmd._get_payload()
    assert isinstance(payload, dict)
    _verify_header(payload)
    assert payload["body"]["data"] == {"childLock": enable}


@pytest.mark.parametrize("enable", [True, False])
def test_native_auto_boost_command(*, enable: bool) -> None:
    cmd = NativeSetAutoBoost(enable)
    assert cmd.NAME == "50036"
    assert cmd._args == {"autoBoost": enable}
    payload = cmd._get_payload()
    assert isinstance(payload, dict)
    _verify_header(payload)
    assert payload["body"]["data"] == {"autoBoost": enable}


@pytest.mark.parametrize("enable", [True, False])
def test_native_continuous_cleaning_command(*, enable: bool) -> None:
    cmd = NativeSetContinuousCleaning(enable)
    assert cmd.NAME == "50025"
    assert cmd._args == {"breakCleanSwitch": enable}
    payload = cmd._get_payload()
    assert isinstance(payload, dict)
    _verify_header(payload)
    assert payload["body"]["data"] == {"breakCleanSwitch": enable}


@pytest.mark.parametrize("enable", [True, False])
def test_native_do_not_disturb_command(*, enable: bool) -> None:
    cmd = NativeSetDoNotDisturb(enable)
    assert cmd.NAME == "50019"
    assert cmd._args == {"disturbSwitch": enable}
    payload = cmd._get_payload()
    assert isinstance(payload, dict)
    _verify_header(payload)
    assert payload["body"]["data"] == {"disturbSwitch": enable}


@pytest.mark.parametrize("volume", [0, 5, 10])
def test_native_volume_command(volume: int) -> None:
    cmd = NativeSetVolume(volume)
    assert cmd.NAME == "50023"
    assert cmd._args == {"volume": volume}
    payload = cmd._get_payload()
    assert isinstance(payload, dict)
    _verify_header(payload)
    assert payload["body"]["data"] == {"volume": volume}


@pytest.mark.parametrize(
    ("cmd_cls", "field_name", "value"),
    [
        (NativeSetChildLock, "childLock", True),
        (NativeSetChildLock, "childLock", False),
        (NativeSetAutoBoost, "autoBoost", True),
        (NativeSetAutoBoost, "autoBoost", False),
        (NativeSetContinuousCleaning, "breakCleanSwitch", True),
        (NativeSetContinuousCleaning, "breakCleanSwitch", False),
        (NativeSetDoNotDisturb, "disturbSwitch", True),
        (NativeSetDoNotDisturb, "disturbSwitch", False),
    ],
)
def test_native_bool_mqtt_reconstruction(
    cmd_cls: type[Any], field_name: str, *, value: bool
) -> None:
    raw = orjson.dumps({"body": {"data": {field_name: value}}})
    restored = cmd_cls.create_from_mqtt(raw)
    assert restored == cmd_cls(value)
    assert restored._args == {field_name: value}


@pytest.mark.parametrize("level", [0, 5, 10])
def test_native_volume_mqtt_reconstruction(level: int) -> None:
    raw = orjson.dumps({"body": {"data": {"volume": level}}})
    restored = NativeSetVolume.create_from_mqtt(raw)
    assert restored == NativeSetVolume(level)
    assert restored._args == {"volume": level}


@pytest.mark.parametrize("invalid", [1, 0, "false", "true", None])
@pytest.mark.parametrize(
    "cmd_cls",
    [
        NativeSetChildLock,
        NativeSetAutoBoost,
        NativeSetContinuousCleaning,
        NativeSetDoNotDisturb,
    ],
)
def test_native_bool_invalid_constructor(cmd_cls: type[Any], invalid: Any) -> None:
    with pytest.raises(TypeError, match="enable must be a boolean"):
        cmd_cls(invalid)


@pytest.mark.parametrize("invalid", [True, False, -1, 11])
def test_native_volume_invalid_constructor(invalid: Any) -> None:
    with pytest.raises(ValueError, match="Volume must be an integer between 0 and 10"):
        NativeSetVolume(invalid)


@pytest.mark.parametrize("invalid", [True, False, -1, 11, "foo"])
def test_native_volume_invalid_mqtt(invalid: Any) -> None:
    raw = orjson.dumps({"body": {"data": {"volume": invalid}}})
    with pytest.raises(DeebotError):
        NativeSetVolume.create_from_mqtt(raw)


@pytest.mark.parametrize(
    ("cmd_cls", "field_name", "invalid"),
    [
        (NativeSetChildLock, "childLock", 1),
        (NativeSetChildLock, "childLock", "true"),
        (NativeSetAutoBoost, "autoBoost", 0),
        (NativeSetContinuousCleaning, "breakCleanSwitch", "false"),
        (NativeSetDoNotDisturb, "disturbSwitch", 1),
    ],
)
def test_native_bool_invalid_mqtt(
    cmd_cls: type[Any], field_name: str, invalid: Any
) -> None:
    raw = orjson.dumps({"body": {"data": {field_name: invalid}}})
    with pytest.raises(DeebotError):
        cmd_cls.create_from_mqtt(raw)


@pytest.mark.parametrize(
    "command",
    [
        NativeSetChildLock(True),
        NativeSetAutoBoost(True),
        NativeSetContinuousCleaning(True),
        NativeSetDoNotDisturb(True),
        NativeSetVolume(5),
    ],
)
def test_native_setting_failed_reply_no_event(command: Any) -> None:
    event_bus = Mock(spec_set=EventBus)
    failed_body = orjson.dumps({"body": {"code": 500, "msg": "fail"}})
    command.handle_mqtt_p2p(event_bus, failed_body)
    event_bus.notify.assert_not_called()
