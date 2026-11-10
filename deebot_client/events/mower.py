"""Mower event module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, unique

from .base import Event


@unique
class CutEfficiency(IntEnum):
    """Enum class for all possible cut efficiency levels."""

    EFFICIENT = 1
    FINE = 2


@dataclass(frozen=True)
class CutEfficiencyEvent(Event):
    """Cut efficiency event representation."""

    efficiency: CutEfficiency
