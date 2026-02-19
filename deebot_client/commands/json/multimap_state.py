"""Multimap state command module."""

from deebot_client.events import MultimapStateEvent

from .common import GetEnableCommand, SetEnableCommand


class GetMultimapState(GetEnableCommand):
    """Get multimap state command."""

    NAME = "getMultiMapState"
    EVENT_TYPE = MultimapStateEvent


class SetMultimapState(SetEnableCommand):
    """Set multimap state command."""

    NAME = "setMultiMapState"
    get_command = GetMultimapState
