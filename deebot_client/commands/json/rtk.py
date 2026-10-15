"""RTK commands."""

from __future__ import annotations

from deebot_client.messages.json.rtk import OnRtk

from .common import JsonCommandWithMessageHandling


class GetRtk(OnRtk, JsonCommandWithMessageHandling):
    """Get RTK command."""

    NAME = "getRTK"
