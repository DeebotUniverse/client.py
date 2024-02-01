"""SweepMode command module for "Mop-Only" option."""
from __future__ import annotations

from deebot_client.events import SweepModeEvent

from .common import GetEnableCommand, SetEnableCommand


class GetSweepMode(GetEnableCommand):
    """GetSweepMode command."""

    name = "getSweepMode"
    event_type = SweepModeEvent
    _field_name = "type"


class SetSweepMode(SetEnableCommand):
    """SetSweepMode command."""

    name = "setSweepMode"
    get_command = GetSweepMode
    _field_name = "type"
