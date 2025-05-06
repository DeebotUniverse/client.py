"""Auto cut direction command module."""

from __future__ import annotations

from deebot_client.events import AutoCutDirectionEvent

from .common import GetEnableCommand, SetEnableCommand


class GetAutoCutDirection(GetEnableCommand):
    """Get auto cut direction command."""

    NAME = "getAutoCutDirection"
    EVENT_TYPE = AutoCutDirectionEvent


class SetAutoCutDirection(SetEnableCommand):
    """Set auto cut direction command."""

    NAME = "setAutoCutDirection"
    get_command = GetAutoCutDirection
