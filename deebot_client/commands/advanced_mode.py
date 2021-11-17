"""Advanced mode command module."""

from ..events import AdvancedModeEvent
from .common import SetEnableCommand, _GetEnableCommand


class GetAdvancedMode(_GetEnableCommand):
    """Get advanced mode command."""

    name = "getAdvancedMode"
    event_type = AdvancedModeEvent


class SetAdvancedMode(SetEnableCommand):
    """Set advanced mode command."""

    name = "setAdvancedMode"
    get_command = GetAdvancedMode
