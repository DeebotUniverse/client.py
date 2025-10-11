"""Cross map border warning commands."""

from __future__ import annotations

from deebot_client.events import CrossMapBorderWarningEvent

from .common import GetEnableCommand, SetEnableCommand


class GetCrossMapBorderWarning(GetEnableCommand):
    """Get cross map border warning command."""

    NAME = "getCrossMapBorderWarning"
    EVENT_TYPE = CrossMapBorderWarningEvent


class SetCrossMapBorderWarning(SetEnableCommand):
    """Set cross map border warning command."""

    NAME = "setCrossMapBorderWarning"
    get_command = GetCrossMapBorderWarning
