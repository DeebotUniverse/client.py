"""Play sound commands."""

from __future__ import annotations

from .common import ExecuteCommand


class PlaySound(ExecuteCommand):
    """Play sound command."""

    NAME = "playSound"

    def __init__(self) -> None:
        super().__init__({"count": 1, "sid": 30})
