"""Continuous cleaning (break point) command module."""

from __future__ import annotations

from deebot_client.events import ContinuousCleaningEvent

from .common import GetEnableCommand, SetEnableCommand


class GetContinuousCleaning(GetEnableCommand):
    """Get continuous cleaning command."""

    NAME = "getBreakPoint"
    event_type = ContinuousCleaningEvent


class SetContinuousCleaning(SetEnableCommand):
    """Set continuous cleaning command."""

    NAME = "setBreakPoint"
    get_command = GetContinuousCleaning
