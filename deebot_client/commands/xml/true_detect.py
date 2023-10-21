"""True detect command module."""

from deebot_client.events import TrueDetectEvent

from .common import GetEnableCommand, SetEnableCommand


class GetTrueDetect(GetEnableCommand):
    """Get multimap state command."""

    name = "GetTrueDetect"

    event_type = TrueDetectEvent


class SetTrueDetect(SetEnableCommand):
    """Set multimap state command."""

    name = "SetTrueDetect"

    get_command = GetTrueDetect
