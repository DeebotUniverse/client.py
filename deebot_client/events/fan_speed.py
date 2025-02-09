"""Fan speed event module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, unique
from typing import Self

from .base import Event


@unique
class FanSpeedLevel(IntEnum):
    """Enum class for all possible fan speed levels."""

    xml_value: str

    def __new__(cls, value: int, xml_value: str = "") -> Self:
        """Get new instance."""
        obj = int.__new__(cls)
        obj._value_ = value
        obj.xml_value = xml_value
        return obj

    @classmethod
    def from_xml(cls, value: str) -> FanSpeedLevel:
        """Get FanSpeedLevel from xml value."""
        for fan_speed_level in FanSpeedLevel:
            if fan_speed_level.xml_value == value:
                return fan_speed_level

        msg = f"{value} is not a valid {cls.__name__}"
        raise ValueError(msg)

    # Values should be sort from low to high on their meanings
    QUIET = 1000, ""
    NORMAL = 0, "standard"
    MAX = 1, "strong"
    MAX_PLUS = 2, ""


@dataclass(frozen=True)
class FanSpeedEvent(Event):
    """Fan speed event representation."""

    speed: FanSpeedLevel
