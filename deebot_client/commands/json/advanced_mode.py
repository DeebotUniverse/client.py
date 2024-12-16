"""Advanced mode command module."""

from __future__ import annotations

from deebot_client.events import AdvancedModeEvent

from .common import GetEnableCommand, SetEnableCommand


class GetAdvancedMode(GetEnableCommand):
    """Get advanced mode command."""

    NAME = "getAdvancedMode"
    event_type = AdvancedModeEvent


class SetAdvancedMode(SetEnableCommand):
    """Set advanced mode command."""

    NAME = "setAdvancedMode"
    get_command = GetAdvancedMode
