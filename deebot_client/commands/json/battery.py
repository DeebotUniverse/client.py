"""Battery commands."""

from __future__ import annotations

from deebot_client.messages.json import OnBattery

from .common import JsonCommandWithMessageHandling


class GetBattery(OnBattery, JsonCommandWithMessageHandling):
    """Get battery command."""

    name = "getBattery"

    def __init__(self, *, is_available_check: bool = False) -> None:
        super().__init__()
        self._is_available_check = is_available_check
