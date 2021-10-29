"""Water info event module."""
from dataclasses import dataclass

from ..util import DisplayNameIntEnum
from .base import EventDto


class WaterAmount(DisplayNameIntEnum):
    """Enum class for all possible water amounts."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    ULTRAHIGH = 4


@dataclass(frozen=True)
class WaterInfoEventDto(EventDto):
    """Water info event representation."""

    mop_attached: bool
    amount: WaterAmount
