"""True detect command module."""

from ..events import TrueDetectEvent
from .common import GetEnableCommand, SetEnableCommand


class GetTrueDetect(GetEnableCommand):
    """Get multimap state command."""

    name = "getTrueDetect"

    xml_name = "GetTrueDetect"

    event_type = TrueDetectEvent


class SetTrueDetect(SetEnableCommand):
    """Set multimap state command."""

    name = "setTrueDetect"

    xml_name = "SetTrueDetect"

    get_command = GetTrueDetect
