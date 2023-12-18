"""Cleaning pads interval event module."""
from dataclasses import dataclass

from .base import Event


@dataclass(frozen=True)
class WashIntervalEvent(Event):
    """Cleaning pads interval event representation."""

    interval: int
