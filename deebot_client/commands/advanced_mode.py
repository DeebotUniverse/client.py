"""Advanced mode command module."""

from ..events import AdvancedModeEvent
from .common import GetEnableCommand, SetEnableCommand


class GetAdvancedMode(GetEnableCommand):
    """Get advanced mode command."""

    name = "getAdvancedMode"

    # TODO Potentially not available on XML based models?
    xml_name = "GetAdvancedMode"

    event_type = AdvancedModeEvent


class SetAdvancedMode(SetEnableCommand):
    """Set advanced mode command."""

    name = "setAdvancedMode"

    # TODO Potentially not available on XML based models?
    xml_name = "SetAdvancedMode"

    get_command = GetAdvancedMode
