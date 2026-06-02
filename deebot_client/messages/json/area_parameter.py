"""Command to set area parameters for mowers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base import JsonCommand


@dataclass(frozen=True)
class SetAreaParameter(JsonCommand):
    """Set Area Parameter command (mow height, cut angle)."""

    area_id: str | int
    angle: int
    mow_height_level: int
    cut_mode: int = 7
    obstacle_height: int = 1

    @property
    def name(self) -> str:
        """Return the command name."""
        return "setAreaParameter"

    def get_payload(self) -> dict[str, Any]:
        """Return the payload formatted for the mower."""
        return {
            "areaParameters": [
                {
                    "areaID": str(self.area_id),
                    "angle": self.angle,
                    "mowHeightLevel": self.mow_height_level,
                    "cutMode": self.cut_mode,
                    "obstacleHeight": self.obstacle_height,
                }
            ]
        }
