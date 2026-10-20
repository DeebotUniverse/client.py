"""Area parameter commands."""

from __future__ import annotations

from .common import ExecuteCommand


class SetAreaParameter(ExecuteCommand):
    """Set parameters for a mower area."""

    NAME = "setAreaParameter"

    def __init__(
        self,
        area_id: str,
        mow_height_level: int,
        cut_mode: int,
        obstacle_height: int,
        angle: int,
    ) -> None:
        super().__init__(
            {
                "areaID": area_id,
                "mowHeightLevel": mow_height_level,
                "cutMode": cut_mode,
                "obstacleHeight": obstacle_height,
                "angle": angle,
            }
        )
