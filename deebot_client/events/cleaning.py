"""Raw room progress and final statistics; neither implies successful completion."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Event


@dataclass(frozen=True)
class RoomProgress:
    """One room status reported by the robot, with unmodified protocol values."""

    room_id: int
    status: int
    type: int


@dataclass(frozen=True)
class RoomProgressEvent(Event):
    """Room progress for one robot job and map."""

    cleaning_id: str
    map_id: str
    type: str
    rooms: tuple[RoomProgress, ...]


@dataclass(frozen=True)
class LastCleaningStatsEvent(Event):
    """Final cleaning statistics without an inferred stop reason."""

    start: int
    area: int
    time: int
    type: str
