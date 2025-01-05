"""Auto empty event module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, unique

from .base import Event as _Event

__all__ = ["AutoEmptyEvent", "Frequency"]


@unique
class Frequency(StrEnum):
    """Enum class for all possible frequencies."""

    MIN_10 = "10"
    MIN_15 = "15"
    MIN_25 = "25"
    AUTO = "auto"
    SMART = "smart"


@dataclass(frozen=True)
class AutoEmptyEvent(_Event):
    """Auto empty event representation."""

    enabled: bool
    frequency: Frequency | None = None
