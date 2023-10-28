"""Advanced mode command module."""

from deebot_client.events import AdvancedModeEvent

from .common import GetEnableCommand, SetEnableCommand


class GetAdvancedMode(GetEnableCommand):
    """Get advanced mode command."""

    name = "getAdvancedMode"
    event_type = AdvancedModeEvent


class SetAdvancedMode(SetEnableCommand):
    """Set advanced mode command."""

    name = "setAdvancedMode"
    get_command = GetAdvancedMode
