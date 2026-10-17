"""Narrow passage adaptation commands."""

from __future__ import annotations

from deebot_client.events import NarrowAdaptEvent

from .common import GetEnableCommand, SetEnableCommand


class GetNarrowAdapt(GetEnableCommand):
    """Get narrow passage adaptation state."""

    NAME = "getNarrowAdapt"
    EVENT_TYPE = NarrowAdaptEvent
    _field_name = "state"


class SetNarrowAdapt(SetEnableCommand):
    """Set narrow passage adaptation state."""

    NAME = "setNarrowAdapt"
    get_command = GetNarrowAdapt
    _field_name = "state"
