"""Area parameter command module."""

from __future__ import annotations

from .common import ExecuteCommand


class SetAreaParameter(ExecuteCommand):
    """Set parameters for a mower area."""

    NAME = "setAreaParameter"

    def __init__(
        self,
        area_id: str | int,
        angle: int,
        mow_height_level: int,
        cut_mode: int = 7,
        obstacle_height: int = 1,
    ) -> None:
        super().__init__(
            {
                "areaID": str(area_id),
                "mowHeightLevel": mow_height_level,
                "cutMode": cut_mode,
                "obstacleHeight": obstacle_height,
                "angle": angle,
            }
        )
