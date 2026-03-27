"""NGIOT play-sound commands."""

from __future__ import annotations

from .common import NgiotExecuteCommand


class PlaySound(NgiotExecuteCommand):
    """Trigger device locate sound."""

    NAME = "seek"

    def __init__(self) -> None:
        super().__init__({"seek": True})