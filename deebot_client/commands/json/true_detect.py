"""True detect command module."""

from __future__ import annotations

from deebot_client.events import TrueDetectEvent

from .common import GetEnableCommand, SetEnableCommand


class GetTrueDetect(GetEnableCommand):
    """Get multimap state command."""

    NAME = "getTrueDetect"
    event_type = TrueDetectEvent


class SetTrueDetect(SetEnableCommand):
    """Set multimap state command."""

    NAME = "setTrueDetect"
    get_command = GetTrueDetect
