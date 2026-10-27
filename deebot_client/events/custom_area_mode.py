"""Custom area mode event module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, unique

from .base import ValueEvent


@unique
class CustomAreaMode(IntEnum):
    """Enum class for the cleaning speed."""

    STANDARD = 0
    DEEP = 1
    QUICK = 2


@dataclass(frozen=True)
class CustomAreaModeEvent(ValueEvent[CustomAreaMode]):
    """Cleaning speed event representation."""
