"""Native numeric setting commands (Y1 Pro cqyi87)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

from deebot_client.command import InitParam

from .native_common import NativeSetCommand
from .native_info import GetNativeInfo


def _validate_bool(val: object, label: str) -> bool:
    if not isinstance(val, bool):
        msg = f"{label} must be a boolean: {val!r}"
        raise TypeError(msg)
    return val


class NativeSetChildLock(NativeSetCommand):
    """Set native child lock (50038)."""

    NAME = "50038"
    get_command = GetNativeInfo
    _mqtt_params = MappingProxyType({"childLock": InitParam(bool, "enable")})

    def __init__(self, enable: bool) -> None:
        super().__init__({"childLock": _validate_bool(enable, "enable")})

    @classmethod
    def _decode(cls, type_: type, value: Any) -> Any:
        if type_ is bool:
            if not isinstance(value, bool):
                msg = f'Could not convert "{value}" of childLock into {type_}'
                raise ValueError(msg)
            return value
        return super()._decode(type_, value)


class NativeSetAutoBoost(NativeSetCommand):
    """Set native carpet auto fan boost (50036)."""

    NAME = "50036"
    get_command = GetNativeInfo
    _mqtt_params = MappingProxyType({"autoBoost": InitParam(bool, "enable")})

    def __init__(self, enable: bool) -> None:
        super().__init__({"autoBoost": _validate_bool(enable, "enable")})

    @classmethod
    def _decode(cls, type_: type, value: Any) -> Any:
        if type_ is bool:
            if not isinstance(value, bool):
                msg = f'Could not convert "{value}" of autoBoost into {type_}'
                raise ValueError(msg)
            return value
        return super()._decode(type_, value)


class NativeSetContinuousCleaning(NativeSetCommand):
    """Set native resume cleaning after charge / breakCleanSwitch (50025)."""

    NAME = "50025"
    get_command = GetNativeInfo
    _mqtt_params = MappingProxyType({"breakCleanSwitch": InitParam(bool, "enable")})

    def __init__(self, enable: bool) -> None:
        super().__init__({"breakCleanSwitch": _validate_bool(enable, "enable")})

    @classmethod
    def _decode(cls, type_: type, value: Any) -> Any:
        if type_ is bool:
            if not isinstance(value, bool):
                msg = f'Could not convert "{value}" of breakCleanSwitch into {type_}'
                raise ValueError(msg)
            return value
        return super()._decode(type_, value)


class NativeSetDoNotDisturb(NativeSetCommand):
    """Set native do not disturb switch (50019)."""

    NAME = "50019"
    get_command = GetNativeInfo
    _mqtt_params = MappingProxyType({"disturbSwitch": InitParam(bool, "enable")})

    def __init__(self, enable: bool) -> None:
        super().__init__({"disturbSwitch": _validate_bool(enable, "enable")})

    @classmethod
    def _decode(cls, type_: type, value: Any) -> Any:
        if type_ is bool:
            if not isinstance(value, bool):
                msg = f'Could not convert "{value}" of disturbSwitch into {type_}'
                raise ValueError(msg)
            return value
        return super()._decode(type_, value)


class NativeSetVolume(NativeSetCommand):
    """Set native voice volume (50023, range 0..10)."""

    NAME = "50023"
    get_command = GetNativeInfo
    _mqtt_params = MappingProxyType({"volume": InitParam(int, "volume")})

    def __init__(self, volume: int) -> None:
        if (
            isinstance(volume, bool)
            or not isinstance(volume, int)
            or not 0 <= volume <= 10
        ):
            msg = f"Volume must be an integer between 0 and 10, got {volume!r}"
            raise ValueError(msg)
        super().__init__({"volume": volume})

    @classmethod
    def _decode(cls, type_: type, value: Any) -> Any:
        if type_ is int:
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= 10
            ):
                msg = f'Could not convert "{value}" of volume into {type_}'
                raise ValueError(msg)
            return value
        return super()._decode(type_, value)
