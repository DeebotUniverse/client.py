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
    EMPTYING = 1


@dataclass(frozen=True)
class StationEvent(_Event):
    """Base Station Event representation."""

    state: State
