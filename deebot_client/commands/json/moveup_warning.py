"""Move up lock commands."""
from __future__ import annotations

from deebot_client.events import MoveUpWarningEvent

from .common import GetEnableCommand, SetEnableCommand


class GetMoveUpWarning(GetEnableCommand):
    """Get move up lock command."""

    name = "getMoveupWarning"
    event_type = MoveUpWarningEvent


class SetMoveUpWarning(SetEnableCommand):
    """Set move up lock command."""

    name = "setMoveupWarning"
    get_command = GetMoveUpWarning
