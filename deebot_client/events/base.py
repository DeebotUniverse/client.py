"""Base event module."""

from dataclasses import dataclass


class Event:
    """Event base class."""


@dataclass(frozen=True)
class ValueEvent[T](Event):
    """Value event class."""

    value: T
