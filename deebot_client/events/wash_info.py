"""Wash info event module."""
from __future__ import annotations

from dataclasses import dataclass

from deebot_client.util import DisplayNameIntEnum

from .base import Event


class WashMode(DisplayNameIntEnum):
    """Enum class for all possible wash modes."""

    STANDARD = 0
    HOT = 1


@dataclass(frozen=True)
class WashInfoEvent(Event):
    """Wash info event representation."""

    mode: WashMode | None
    interval: int | None
    hot_wash_amount: int | None
