"""Water info event module."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, unique

from .base import Event


@unique
class WaterAmount(IntEnum):
    """Enum class for all possible water amounts."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    ULTRAHIGH = 4


@unique
class SweepType(IntEnum):
    """Enum class for all possible sweeping types."""

    STANDARD = 1
    DEEP = 2


@dataclass(frozen=True)
class WaterInfoEvent(Event):
    """Water info event representation."""

    amount: WaterAmount
    # None means no data available
    mop_attached: bool | None = field(kw_only=True, default=None)
    sweep_type: SweepType | None = None
