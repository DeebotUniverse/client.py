"""Advanced mode command module."""

from ..events import AdvancedModeEvent
from .common import _GetEnabledCommand, _SetEnabledCommand


class GetAdvancedMode(_GetEnabledCommand):
    """Get advanced mode command."""

    name = "getAdvancedMode"
    event_type = AdvancedModeEvent


class SetAdvancedMode(_SetEnabledCommand):
    """Set advanced mode command."""

    name = "setAdvancedMode"
    get_command = GetAdvancedMode
