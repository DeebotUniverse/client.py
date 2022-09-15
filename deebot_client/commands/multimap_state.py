"""Multimap state command module."""

from ..events import MultimapStateEvent
from .common import SetEnableCommand, _GetEnableCommand


class GetMultimapState(_GetEnableCommand):
    """Get multimap state command."""

    name = "getMultiMapState"
    event_type = MultimapStateEvent


class SetMultimapState(SetEnableCommand):
    """Set multimap state command."""

    name = "setMultiMapState"
    get_command = GetMultimapState
