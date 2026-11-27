"""Auto empty event module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum, unique

from .base import Event as _Event, ValueEvent

__all__ = [
    "AutoEmptyEvent",
    "AutoEmptyIntensity",
    "AutoEmptyIntensityEvent",
    "Frequency",
]


@unique
class Frequency(StrEnum):
    """Enum class for all possible frequencies."""

    MIN_10 = "10"
    MIN_15 = "15"
    MIN_25 = "25"
    AUTO = "auto"
    SMART = "smart"


@unique
class AutoEmptyIntensity(IntEnum):
    """Enum class for the auto-empty intensity.

    The Ecovacs app labels these values "Standard" and "High Frequency".
    """

    STANDARD = 0
    HIGH_FREQUENCY = 1


@dataclass(frozen=True)
class AutoEmptyEvent(_Event):
    """Auto empty event representation."""

    enabled: bool
    frequency: Frequency | None = None


@dataclass(frozen=True)
class AutoEmptyIntensityEvent(ValueEvent[AutoEmptyIntensity]):
    """Auto empty intensity event representation."""
