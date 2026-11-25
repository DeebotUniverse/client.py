"""RTK status event for mowers (e.g. Ecovacs GOAT family)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import Event


@dataclass(frozen=True, kw_only=True)
class RtkBaseStation:
    """RTK reference (base) station info as reported by the mower."""

    serial_number: str
    """Serial number of the base station, e.g. ``"908276"``."""

    satellites_visible: int
    """Number of satellites currently visible by the base station."""

    firmware: str | None = None
    """Firmware version string reported by the base station, if any."""

    state: int | None = None
    """Raw state code as reported by the device (meaning device-defined)."""

    mode: int | None = None
    """Raw mode code as reported by the device (meaning device-defined)."""


@dataclass(frozen=True)
class RtkEvent(Event):
    """RTK status snapshot for a mower.

    The Ecovacs GOAT family pairs a reference (base) station with a
    rover (the mower itself) and a Real-Time-Kinematic correction loop.
    The official Ecovacs Home app surfaces the relevant counters under
    "Settings → RTK" of the device. This event mirrors that screen.
    """

    rover_serial_number: str
    """Serial number of the rover (mower), e.g. ``"908336"``."""

    rover_satellites_visible: int
    """Total number of satellites the rover currently sees."""

    rover_satellites_used: int
    """Satellites actually used in the rover's RTK solution."""

    base_satellites_used: int
    """Satellites actually used in the base station's RTK solution."""

    rover_signal_score: int
    """Quality score (0-100) of the rover's GNSS signal."""

    base_signal_score: int
    """Quality score (0-100) of the base station's GNSS signal."""

    rover_occlusion_rate: int
    """Estimated rover sky-occlusion rate (percent)."""

    base_occlusion_rate: int
    """Estimated base sky-occlusion rate (percent)."""

    base_stations: list[RtkBaseStation] = field(default_factory=list)
    """One entry per known reference station (usually exactly one)."""

    base_station_id: str | None = None
    """ID of the base station currently providing corrections, if any."""

    solution_status: int | None = None
    """Raw ``solStat`` from the device (meaning device-defined)."""

    pose_type: int | None = None
    """Raw ``poseType`` from the device (meaning device-defined)."""
