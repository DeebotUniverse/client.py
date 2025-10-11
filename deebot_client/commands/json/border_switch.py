"""Border switch commands."""

from __future__ import annotations

from deebot_client.events import BorderSwitchEvent

from .common import GetEnableCommand, SetEnableCommand


class GetBorderSwitch(GetEnableCommand):
    """Get border switch command."""

    NAME = "getBorderSwitch"
    EVENT_TYPE = BorderSwitchEvent


class SetBorderSwitch(SetEnableCommand):
    """Set border switch command."""

    NAME = "setBorderSwitch"
    get_command = GetBorderSwitch
