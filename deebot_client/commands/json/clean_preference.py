"""Clean preference command module."""

from __future__ import annotations

from deebot_client.events import CleanPreferenceEvent

from .common import GetEnableCommand, SetEnableCommand


class GetCleanPreference(GetEnableCommand):
    """Get clean preference command."""

    NAME = "getCleanPreference"
    EVENT_TYPE = CleanPreferenceEvent


class SetCleanPreference(SetEnableCommand):
    """Set clean preference command."""

    NAME = "setCleanPreference"
    get_command = GetCleanPreference
