"""Shared native numeric command base (Y1 Pro cloudctl/rop header)."""

from __future__ import annotations

from abc import ABC
import time
from typing import Any

from .common import ExecuteCommand, JsonCommand, JsonGetCommand, JsonSetCommand


def native_header() -> dict[str, Any]:
    """Build the exact native request header."""
    return {
        "pri": 3,
        "m": "cloudctl",
        "channel": "rop",
        "ver": "0.0.1",
        "tzm": 480,
        "ts": str(int(time.time() * 1000)),
    }


class NativeJsonCommand(JsonCommand, ABC):
    """Json command using the native numeric header."""

    def _get_payload(self) -> dict[str, Any] | list[Any]:
        return {"header": native_header(), "body": {"data": self._args}}


class NativeExecuteCommand(NativeJsonCommand, ExecuteCommand, ABC):
    """Native command executing something (no state invented from ACK)."""


class NativeGetCommand(NativeJsonCommand, JsonGetCommand, ABC):
    """Native get command."""


class NativeSetCommand(NativeExecuteCommand, JsonSetCommand, ABC):
    """Native set command linked to a get command for sensor updates."""
