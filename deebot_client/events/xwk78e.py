"""China T80 station setting events."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, unique

from deebot_client.events.auto_empty import AutoEmptyEvent
from deebot_client.events.base import Event


@unique
class AutoEmptyIntensity(IntEnum):
    """T80 station suction intensity values."""

    STANDARD = 1
    SILENT = 0


@dataclass(frozen=True)
class AutoEmptyEventT80(AutoEmptyEvent):
    """T80 auto-empty state including station suction intensity."""

    intensity: AutoEmptyIntensity | None = None


@unique
class TrueDetectLevel(IntEnum):
    """T80 obstacle detection sensitivity values."""

    HIGH_SENSITIVITY = 0
    STANDARD = 1


@dataclass(frozen=True)
class TrueDetectLevelEvent(Event):
    """T80 obstacle detection sensitivity state."""

    level: TrueDetectLevel


@unique
class WashMode(IntEnum):
    """T80 station mop-washing modes."""

    SMART_TEMPERATURE = 3
    ENERGY_SAVING = 0
    HOT_WATER_STANDARD = 1
    HOT_WATER_DEEP = 2


@dataclass(frozen=True)
class WashModeEvent(Event):
    """T80 station mop-washing mode state."""

    mode: WashMode
    interval: int | None = None
