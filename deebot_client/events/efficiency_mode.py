"""Efficiency mode event module."""
from dataclasses import dataclass

from deebot_client.util import DisplayNameIntEnum

from .base import Event


class EfficiencyMode(DisplayNameIntEnum):
    """Enum class for all possible efficiency modes."""

    STANDART_MODE = 0
    ENERGY_EFFICIENT_MODE = 1


@dataclass(frozen=True)
class EfficiencyModeEvent(Event):
    """Efficiency mode event representation."""

    efficiency: EfficiencyMode
