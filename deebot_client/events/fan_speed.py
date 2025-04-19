"""Fan speed event module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import unique

from deebot_client.util.enum import IntEnumWithXml

from .base import Event


@unique
class FanSpeedLevel(IntEnumWithXml):
    """Enum class for all possible fan speed levels."""

    # Values should be sort from low to high on their meanings
    QUIET = 1000
    NORMAL = 0, "standard"
    MAX = 1, "strong"
    MAX_PLUS = 2


@dataclass(frozen=True)
class FanSpeedEvent(Event):
    """Fan speed event representation."""

    speed: FanSpeedLevel
