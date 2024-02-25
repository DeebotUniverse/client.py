"""Child lock commands."""
from __future__ import annotations

from deebot_client.events import ChildLockEvent

from .common import GetEnableCommand, SetEnableCommand


class GetChildLock(GetEnableCommand):
    """Get child lock command."""

    name = "getChildLock"
    event_type = ChildLockEvent
    _field_name = "on"


class SetChildLock(SetEnableCommand):
    """Set child lock command."""

    name = "setChildLock"
    get_command = GetChildLock
    _field_name = "on"
