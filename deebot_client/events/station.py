"""Base station event module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, unique

from .base import Event as _Event

__all__ = ["State", "StationErrorEvent", "StationEvent"]


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


@dataclass(frozen=True)
class StationErrorEvent(_Event):
    """Errors reported by the base station, e.g. a water-tank condition.

    ``errors`` holds the raw Ecovacs codes exactly as reported, including the
    0/100 "no error" sentinels; map them via
    :data:`deebot_client.const.ERROR_CODES`. An empty tuple means the station
    reported an empty error list.
    """

    errors: tuple[int, ...]
