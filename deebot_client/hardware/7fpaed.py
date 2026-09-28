"""DEEBOT T90 OMNI (7fpaed) capabilities."""

from __future__ import annotations

from dataclasses import replace
import time
from typing import Any

from deebot_client.commands.json.clean import CleanV2
from deebot_client.hardware.twunby import get_device_info as get_twunby_device_info
from deebot_client.models import CleanAction, CleanMode, StaticDeviceInfo


class _CleanV2(CleanV2):
    """Serialize clean actions as expected by the T90 OMNI."""

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        args: dict[str, Any] = {"act": action.value}
        if action != CleanAction.STOP:
            args.update(
                {
                    "content": {"type": CleanMode.AUTO.value},
                    "noVoiceResp": 0,
                }
            )
        return args

    def _get_payload(self) -> dict[str, Any] | list[Any]:
        if (
            isinstance(self._args, dict)
            and self._args.get("act") == CleanAction.STOP.value
        ):
            return super()._get_payload()

        return {
            "header": {
                "ver": 0.1,
                "priority": 1,
                "ts": int(time.time() * 1000),
                "channel": "ROP",
            },
            "body": {"data": self._args},
        }


def get_device_info() -> StaticDeviceInfo:
    """Get device info for the DEEBOT T90 OMNI."""
    device_info = get_twunby_device_info()
    capabilities = device_info.capabilities
    clean = capabilities.clean
    action = replace(clean.action, command=_CleanV2)
    return replace(
        device_info,
        capabilities=replace(capabilities, clean=replace(clean, action=action)),
    )
