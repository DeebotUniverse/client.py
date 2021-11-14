"""Break point (continuous cleaning) command module."""

from ..events import BreakPointEvent
from .common import SetEnableCommand, _GetEnableCommand


class GetBreakPoint(_GetEnableCommand):
    """Get break point (continuous cleaning) command."""

    name = "getBreakPoint"
    event_type = BreakPointEvent


class SetBreakPoint(SetEnableCommand):
    """Set break point (continuous cleaning) command."""

    name = "setBreakPoint"
    get_command = GetBreakPoint
