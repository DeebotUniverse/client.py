"""Rain delay events."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Event


@dataclass(frozen=True)
class RainDelayEvent(Event):
    """Rain sensor configuration, with delay expressed in minutes."""

    enabled: bool
    delay: int
