"""Native numeric info commands (Y1 Pro 10001 query)."""

from __future__ import annotations

from deebot_client.messages.json.native_info import OnNativeInfo

from .native_common import NativeGetCommand

_DEFAULT_FIELDS: list[str] = [
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


class GetNativeInfo(OnNativeInfo, NativeGetCommand):
    """Get native info command (numeric 10001 with fields selector)."""

    NAME = "10001"

    def __init__(
        self, fields: list[str] | None = None, *, is_available_check: bool = False
    ) -> None:
        super().__init__(
            {"fields": list(fields) if fields is not None else list(_DEFAULT_FIELDS)}
        )
        self._is_available_check = is_available_check
