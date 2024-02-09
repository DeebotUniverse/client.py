"""Continuous cleaning (break point) command module."""
from __future__ import annotations

from deebot_client.events import ContinuousCleaningEvent

from .common import GetEnableCommand, SetEnableCommand


class GetContinuousCleaning(GetEnableCommand):
    """Get continuous cleaning command."""

    name = "getBreakPoint"
    event_type = ContinuousCleaningEvent


class SetContinuousCleaning(SetEnableCommand):
    """Set continuous cleaning command."""

    name = "setBreakPoint"
    get_command = GetContinuousCleaning
