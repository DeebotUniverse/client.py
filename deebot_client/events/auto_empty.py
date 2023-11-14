"""Auto empty event module."""
from dataclasses import dataclass

from deebot_client.util import DisplayNameStrEnum

from .base import Event


class AutoEmptyMode(DisplayNameStrEnum):
    """Enum class for all possible auto emptys."""

    MODE_10 = "10"
    MODE_15 = "15"
    MODE_25 = "25"
    MODE_AUTO = "auto"


@dataclass(frozen=True)
class AutoEmptyModeEvent(Event):
    """Auto empty event representation."""

    enable: bool
    mode: AutoEmptyMode
