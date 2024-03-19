"""Efficiency mode event module."""

from __future__ import annotations

from dataclasses import dataclass

from deebot_client.util import DisplayNameIntEnum

from .base import Event


class EfficiencyMode(DisplayNameIntEnum):
    """Enum class for all possible efficiency modes."""

    STANDARD_MODE = 0
    ENERGY_EFFICIENT_MODE = 1


@dataclass(frozen=True)
class EfficiencyModeEvent(Event):
    """Efficiency mode event representation."""

    efficiency: EfficiencyMode
