"""Cleaning pads interval event module."""
from dataclasses import dataclass

from .base import Event


@dataclass(frozen=True)
class WashIntervalEvent(Event):
    """Wash interval event representation."""

    interval: int
