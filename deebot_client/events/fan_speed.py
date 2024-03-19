"""Fan speed event module."""

from __future__ import annotations

from dataclasses import dataclass

from deebot_client.util import DisplayNameIntEnum

from .base import Event


class FanSpeedLevel(DisplayNameIntEnum):
    """Enum class for all possible fan speed levels."""

    # Values should be sort from low to high on their meanings
    QUIET = 1000
    NORMAL = 0
    MAX = 1
    MAX_PLUS = 2


@dataclass(frozen=True)
class FanSpeedEvent(Event):
    """Fan speed event representation."""

    speed: FanSpeedLevel
