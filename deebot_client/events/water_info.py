"""Water info event module."""

from __future__ import annotations

from enum import IntEnum, unique

from .base import ValueEvent

__all__ = [
    "MopAttachedEvent",
    "SweepType",
    "WaterAmount",
    "WaterAmountEvent",
    "WaterSweepTypeEvent",
]


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


class WaterAmountEvent(ValueEvent[WaterAmount]):
    """Water amount event."""


class WaterSweepTypeEvent(ValueEvent[SweepType]):
    """Water sweep type event."""


class MopAttachedEvent(ValueEvent[bool]):
    """Mop attached event."""
