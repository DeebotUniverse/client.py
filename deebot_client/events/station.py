"""Base station event module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, unique

from .base import Event as _Event

__all__ = ["State", "StationEvent"]


@unique
class State(IntEnum):
    """Enum class for all possible base station statuses."""

    IDLE = 0
    EMPTYING_DUSTBIN = 1
    WASHING_MOP = 2
    DRYING_MOP = 3


@dataclass(frozen=True)
class StationEvent(_Event):
    """Base Station Event representation."""

    state: State
