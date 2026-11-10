"""Wash info event module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, unique

from .base import Event

__all__ = [
    "MopAutoWashMode",
    "MopAutoWashModeEvent",
    "MopWashMode",
    "MopWashModeEvent",
]


@unique
class MopWashMode(IntEnum):
    """Enum class for all possible mop wash modes ("Wash method" in the app)."""

    ECO = 0
    STANDARD = 1
    DEEP = 2
    INTELLIGENT_TEMPERATURE = 3


@unique
class MopAutoWashMode(IntEnum):
    """Enum class for all possible mop auto-wash modes.

    Only BY_TIME uses the mop auto-wash frequency (interval).
    """

    BY_TIME = 0
    BY_ROOM = 1
    SMART = 2


@dataclass(frozen=True)
class MopWashModeEvent(Event):
    """Mop wash mode event representation."""

    mode: MopWashMode


@dataclass(frozen=True)
class MopAutoWashModeEvent(Event):
    """Mop auto-wash mode event representation."""

    mode: MopAutoWashMode
