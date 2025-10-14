"""Base event module."""

from __future__ import annotations

from dataclasses import dataclass


class Event:
    """Event base class."""


@dataclass(frozen=True)
class ValueEvent[T](Event):
    """Value event class."""

    value: T
