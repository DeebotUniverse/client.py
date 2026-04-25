"""Mop Auto-Wash Frequency event module."""

from dataclasses import dataclass

from .base import ValueEvent


@dataclass(frozen=True)
class MopAutoWashFrequencyEvent(ValueEvent[int]):
    """Mop Auto-Wash Frequency event representation."""
