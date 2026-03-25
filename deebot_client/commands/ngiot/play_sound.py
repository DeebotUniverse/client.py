"""Play-sound commands."""

# deebot_client/commands/json/seek_sound.py
"""Seek sound / locate command for NGIOT eyfj07."""

from __future__ import annotations

from .common import ExecuteCommand

class SeekSound(ExecuteCommand):
    """Trigger device locate sound on eyfj07-like devices."""

    NAME = "seek"

    def __init__(self) -> None:
        super().__init__({"seek": True})