"""Safe protect commands."""

from __future__ import annotations

from deebot_client.events import SafeProtectEvent

from .common import GetEnableCommand, SetEnableCommand


class GetSafeProtect(GetEnableCommand):
    """Get safe protect command."""

    NAME = "getSafeProtect"
    EVENT_TYPE = SafeProtectEvent


class SetSafeProtect(SetEnableCommand):
    """Set safe protect command."""

    NAME = "setSafeProtect"
    get_command = GetSafeProtect
