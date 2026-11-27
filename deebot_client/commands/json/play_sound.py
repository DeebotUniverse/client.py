"""Play sound commands."""

from __future__ import annotations

from .common import ExecuteCommand


class PlaySound(ExecuteCommand):
    """Play sound command."""

    NAME = "playSound"
    _SOUND_ID = 30

    def __init__(self) -> None:
        super().__init__({"count": 1, "sid": self._SOUND_ID})


class PlayAlarmSound(PlaySound):
    """Play the alarm sound (mowers)."""

    _SOUND_ID = 51
