"""Mower event module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, unique

from .base import Event


@unique
class CutEfficiency(IntEnum):
    """Enum class for all possible cut efficiency levels."""

    EFFICIENT = 1
    FINE = 2


@dataclass(frozen=True)
class CutEfficiencyEvent(Event):
    """Cut efficiency event representation."""

    efficiency: CutEfficiency


@unique
class ObstacleHeight(IntEnum):
    """Enum class for all possible obstacle height levels."""

    LOW = 1  # flat ground with short grass
    NORMAL = 2


@dataclass(frozen=True)
class ObstacleHeightEvent(Event):
    """Obstacle height event representation."""

    height: ObstacleHeight


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


@dataclass(frozen=True, kw_only=True)
class AreaParameter:
    """Mowing parameters of an area."""

    area_id: str
    cut_height: int
    cut_mode: int
    obstacle_height: ObstacleHeight | int


@dataclass(frozen=True)
class AreaParametersEvent(Event):
    """Area parameters event representation."""

    areas: list[AreaParameter]


@dataclass(frozen=True, kw_only=True)
class MowingArea:
    """Mowing area."""

    id: str
    name: str
    label: tuple[float, float] | None = None  # position of the name (mm)


@dataclass(frozen=True)
class MowingAreasEvent(Event):
    """Mowing areas event representation."""

    areas: list[MowingArea]


@dataclass(frozen=True, kw_only=True)
class MowingTaskEvent(Event):
    """Current mowing task event representation."""

    type: str | None
    area_ids: list[str]
    scheduled: bool = False


@dataclass(frozen=True, kw_only=True)
class MowedAreaEvent(Event):
    """Mowed area of the current task in cm²."""

    mowed_area: int
    total_area: int


@dataclass(frozen=True, kw_only=True)
class ProtectStateEvent(Event):
    """Protection state event representation."""

    animal_protection: bool
    rain_protection: bool
    rain_delay: bool
    emergency_stop: bool
    locked: bool


@dataclass(frozen=True, kw_only=True)
class AnimalProtectionEvent(Event):
    """Animal protection (night mowing ban) event representation."""

    enabled: bool
    start: str
    end: str


@dataclass(frozen=True, kw_only=True)
class RainDelayEvent(Event):
    """Rain delay event representation."""

    enabled: bool
    delay: int


@unique
class RtkFixType(IntEnum):
    """Position type of the RTK receiver."""

    NONE = 0
    SINGLE = 16
    PSRDIFF = 17
    FLOAT = 34
    FIXED = 50


@dataclass(frozen=True, kw_only=True)
class RtkBaseStationEvent(Event):
    """RTK base station event representation."""

    state: int
    satellites: int
    position: tuple[float, float] | None = None  # (mm)


@dataclass(frozen=True, kw_only=True)
class RtkSignalEvent(Event):
    """RTK signal event representation."""

    fix_type: RtkFixType | int
    rover_satellites: int
    rover_signal_score: int
    rover_occlusion_rate: int
    base_satellites: int
    base_signal_score: int
    base_occlusion_rate: int
