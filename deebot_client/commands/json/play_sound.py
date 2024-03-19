"""Play sound commands."""

from __future__ import annotations

from .common import ExecuteCommand


class PlaySound(ExecuteCommand):
    """Play sound command."""

    name = "playSound"

    def __init__(self) -> None:
        super().__init__({"count": 1, "sid": 30})
