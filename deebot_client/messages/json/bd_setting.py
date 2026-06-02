"""Parser for bd_setting (Mower Area Settings) messages."""

from __future__ import annotations

from typing import Any

from deebot_client.events import AreaParameter, AreaSettingsEvent

from .base import JsonMessageParser


class BdSettingParser(JsonMessageParser):
    """Parse onFwBuryPoint-bd_setting messages."""

    name = "onFwBuryPoint-bd_setting"

    def parse(self, payload: dict[str, Any]) -> AreaSettingsEvent | None:
        """Parse the payload."""
        body = payload.get("body", {})
        area_params = body.get("AreaParameters")

        if not area_params:
            return None

        parameters = []
        for area in area_params:
            parameters.append(
                AreaParameter(
                    area_id=area["areaID"],
                    angle=area["angle"],
                    mow_height_level=area["mowHeightLevel"],
                    cut_mode=area["cutMode"],
                    obstacle_height=area["obstacleHeight"],
                )
            )

        return AreaSettingsEvent(parameters=parameters)
