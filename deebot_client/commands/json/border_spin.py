"""Border spin commands."""

from __future__ import annotations

from deebot_client.events import BorderSpinEvent

from .common import GetEnableCommand, SetEnableCommand


class GetBorderSpin(GetEnableCommand):
    """Get border spin command."""

    NAME = "getBorderSpin"
    EVENT_TYPE = BorderSpinEvent


class SetBorderSpin(SetEnableCommand):
    """Set border spin command."""

    NAME = "setBorderSpin"
    get_command = GetBorderSpin
