"""Animal protection events."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Event


@dataclass(frozen=True)
class AnimalProtectionEvent(Event):
    """Animal protection schedule."""

    enabled: bool
    start: str
    end: str
