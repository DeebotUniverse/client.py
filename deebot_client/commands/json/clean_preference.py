"""Clean preference command module."""

from deebot_client.events import CleanPreferenceEvent

from .common import GetEnableCommand, SetEnableCommand


class GetCleanPreference(GetEnableCommand):
    """Get clean preference command."""

    name = "getCleanPreference"

    # TODO Potentially not available on XML based models?
    xml_name = "GetCleanPreference"

    event_type = CleanPreferenceEvent


class SetCleanPreference(SetEnableCommand):
    """Set clean preference command."""

    name = "setCleanPreference"

    # TODO Potentially not available on XML based models?
    xml_name = "SetCleanPreference"

    get_command = GetCleanPreference
