"""Child lock commands."""
from __future__ import annotations

from deebot_client.events import ChildLockEvent

from .common import GetEnableCommand, SetEnableCommand


class GetChildLock(GetEnableCommand):
    """Get child lock command."""

    name = "getChildLock"
    event_type = ChildLockEvent


class SetChildLock(SetEnableCommand):
    """Set child lock command."""

    name = "setChildLock"
    get_command = GetChildLock
