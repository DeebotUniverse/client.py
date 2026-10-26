"""Area parameter event module."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Event


@dataclass(frozen=True)
class AreaParameter:
    """Area parameter representation."""

    area_id: str
    mow_height_level: int
    cut_mode: int
    obstacle_height: int
    angle: int


@dataclass(frozen=True)
class AreaParameterEvent(Event):
    """Area parameter event representation."""

    area_parameters: list[AreaParameter]
