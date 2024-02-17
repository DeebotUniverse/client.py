"""Moveup lock commands."""
from __future__ import annotations

from deebot_client.events import MoveupWarningEvent

from .common import GetEnableCommand, SetEnableCommand


class GetMoveupWarning(GetEnableCommand):
    """Get moveup lock command."""

    name = "getMoveupWarning"
    event_type = MoveupWarningEvent


class SetMoveupWarning(SetEnableCommand):
    """Set moveup lock command."""

    name = "setMoveupWarning"
    get_command = GetMoveupWarning
