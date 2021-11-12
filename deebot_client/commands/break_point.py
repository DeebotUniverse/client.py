"""Break point (continuous cleaning) command module."""

from ..events import BreakPointEvent
from .common import _GetEnabledCommand, _SetEnabledCommand


class GetBreakPoint(_GetEnabledCommand):
    """Get break point (continuous cleaning) command."""

    name = "getBreakPoint"
    event_type = BreakPointEvent


class SetBreakPoint(_SetEnabledCommand):
    """Set break point (continuous cleaning) command."""

    name = "setBreakPoint"
    get_command = GetBreakPoint
