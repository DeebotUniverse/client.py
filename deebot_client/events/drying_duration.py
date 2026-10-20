"""Drying duration event module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, unique

from .base import ValueEvent


@unique
class DryingDuration(IntEnum):
    """Enum class for the hot air drying duration."""

    TWO_HOURS = 120
    THREE_HOURS = 180
    FOUR_HOURS = 240


@dataclass(frozen=True)
class DryingDurationEvent(ValueEvent[DryingDuration]):
    """Hot air drying duration event representation."""
