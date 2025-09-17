"""Work state commands."""

from __future__ import annotations

from deebot_client.messages.json.work_state import OnWorkState

from .common import JsonCommandWithMessageHandling


class GetWorkState(OnWorkState, JsonCommandWithMessageHandling):
    """Get work state command."""

    NAME = "getWorkState"
