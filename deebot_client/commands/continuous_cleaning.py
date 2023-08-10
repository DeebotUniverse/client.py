"""Continuous cleaning (break point) command module."""

from ..events import ContinuousCleaningEvent
from .common import GetEnableCommand, SetEnableCommand


class GetContinuousCleaning(GetEnableCommand):
    """Get continuous cleaning command."""

    name = "getBreakPoint"

    # TODO
    xml_name = ""

    event_type = ContinuousCleaningEvent


class SetContinuousCleaning(SetEnableCommand):
    """Set continuous cleaning command."""

    name = "setBreakPoint"

    # TODO
    xml_name = ""

    get_command = GetContinuousCleaning
