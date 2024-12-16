"""Multimap state command module."""

from __future__ import annotations

from deebot_client.events import MultimapStateEvent

from .common import GetEnableCommand, SetEnableCommand


class GetMultimapState(GetEnableCommand):
    """Get multimap state command."""

    NAME = "getMultiMapState"
    event_type = MultimapStateEvent


class SetMultimapState(SetEnableCommand):
    """Set multimap state command."""

    NAME = "setMultiMapState"
    get_command = GetMultimapState
