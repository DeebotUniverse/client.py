"""Clean preference command module."""

from ..events import CleanPreferenceEvent
from .common import GetEnableCommand, SetEnableCommand


class GetCleanPreference(GetEnableCommand):
    """Get clean preference command."""

    name = "getCleanPreference"
    event_type = CleanPreferenceEvent


class SetCleanPreference(SetEnableCommand):
    """Set clean preference command."""

    name = "setCleanPreference"
    get_command = GetCleanPreference
