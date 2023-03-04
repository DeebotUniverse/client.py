"""Water info event module."""
from dataclasses import dataclass

from ..util import DisplayNameIntEnum
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

    # None means no data available
    mop_attached: bool | None
    amount: WaterAmount
