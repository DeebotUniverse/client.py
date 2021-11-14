"""Continuous cleaning (break point) command module."""

from ..events import ContinuousCleaningEvent
from .common import SetEnableCommand, _GetEnableCommand


class GetContinuousCleaning(_GetEnableCommand):
    """Get continuous cleaning command."""

    name = "getBreakPoint"
    event_type = ContinuousCleaningEvent


class SetContinuousCleaning(SetEnableCommand):
    """Set continuous cleaning command."""

    name = "setBreakPoint"
    get_command = GetContinuousCleaning
