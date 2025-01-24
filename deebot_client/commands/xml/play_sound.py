"""Play sound commands."""

from __future__ import annotations

from .common import ExecuteCommand


class PlaySound(ExecuteCommand):
    """Play sound command."""

    NAME = "PlaySound"

    def __init__(self) -> None:
        super().__init__({"sid": "30"})
