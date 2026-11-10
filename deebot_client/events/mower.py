"""Mower event module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, unique

from .base import Event


@unique
class BorderSwitchMode(IntEnum):
    """Enum class for all possible border switch modes."""

    ALONG_BORDER = 0
    EDGE_MOWING = 1
    CROSS_BOUNDARY = 2


@dataclass(frozen=True)
class BorderSwitchModeEvent(Event):
    """Border switch mode event representation."""

    mode: BorderSwitchMode
