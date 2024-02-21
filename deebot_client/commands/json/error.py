"""Error commands."""
from __future__ import annotations

from deebot_client.messages.json import OnError

from .common import JsonCommandWithMessageHandling


class GetError(JsonCommandWithMessageHandling, OnError):
    """Get error command."""

    name = "getError"
