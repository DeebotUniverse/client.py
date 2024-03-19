"""Safe protect commands."""

from __future__ import annotations

from deebot_client.events import SafeProtectEvent

from .common import GetEnableCommand, SetEnableCommand


class GetSafeProtect(GetEnableCommand):
    """Get safe protect command."""

    name = "getSafeProtect"
    event_type = SafeProtectEvent


class SetSafeProtect(SetEnableCommand):
    """Set safe protect command."""

    name = "setSafeProtect"
    get_command = GetSafeProtect
