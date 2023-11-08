"""Auto empty command module."""

from deebot_client.events import AutoEmptyEnableEvent

from .common import GetEnableCommand, SetEnableCommand


class GetAutoEmptyEnable(GetEnableCommand):
    """Get auto empty command."""

    name = "getAutoEmpty"
    event_type = AutoEmptyEnableEvent


class SetAutoEmptyEnable(SetEnableCommand):
    """Set auto empty command."""

    name = "setAutoEmpty"
    get_command = GetAutoEmptyEnable
