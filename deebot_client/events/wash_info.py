"""Wash info event module."""
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

    mode: WashMode
    # None means no data available
    interval: int
    hot_wash_amount: int
