"""Multimap state command module."""

from ..events import MultimapStateEvent
from .common import GetEnableCommand, SetEnableCommand


class GetMultimapState(GetEnableCommand):
    """Get multimap state command."""

    name = "getMultiMapState"

    xml_name = "GetMultiMapState"

    event_type = MultimapStateEvent


class SetMultimapState(SetEnableCommand):
    """Set multimap state command."""

    name = "setMultiMapState"

    xml = "SetMultiMapState"

    get_command = GetMultimapState
