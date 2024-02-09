"""Water info event module."""
from __future__ import annotations

from dataclasses import dataclass, field

from deebot_client.util import DisplayNameIntEnum

from .base import Event


class WaterAmount(DisplayNameIntEnum):
    """Enum class for all possible water amounts."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    ULTRAHIGH = 4


@dataclass(frozen=True)
class WaterInfoEvent(Event):
    """Water info event representation."""

    amount: WaterAmount
    # None means no data available
    mop_attached: bool | None = field(kw_only=True, default=None)
