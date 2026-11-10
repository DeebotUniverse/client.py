"""Status event module (break-point, map state, relocation)."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Event


@dataclass(frozen=True)
class BreakPointStatusEvent(Event):
    """Continuous-cleaning break-point status."""

    status: int
    is_conflict: bool
    continue_left_time: int  # in seconds


@dataclass(frozen=True)
class MapStateEvent(Event):
    """Map state."""

    state: str


@dataclass(frozen=True)
class RelocationStateEvent(Event):
    """Relocation state."""

    has_map: bool
    mode: str
    state: str
