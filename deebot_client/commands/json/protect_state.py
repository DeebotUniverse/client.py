"""Protect state commands."""

from __future__ import annotations

from deebot_client.messages.json.protect_state import OnProtectState

from .common import JsonCommandWithMessageHandling


class GetProtectState(OnProtectState, JsonCommandWithMessageHandling):
    """Get protect state command."""

    NAME = "getProtectState"
