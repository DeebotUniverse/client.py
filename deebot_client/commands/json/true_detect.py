"""True detect command module."""
from __future__ import annotations

from deebot_client.events import TrueDetectEvent

from .common import GetEnableCommand, SetEnableCommand


class GetTrueDetect(GetEnableCommand):
    """Get true detect command."""

    name = "getTrueDetect"
    event_type = TrueDetectEvent


class SetTrueDetect(SetEnableCommand):
    """Set true detect command."""

    name = "setTrueDetect"
    get_command = GetTrueDetect
