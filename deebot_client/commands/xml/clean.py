"""Clean commands."""

from __future__ import annotations

from deebot_client.models import CleanAction, CleanMode

from .common import ExecuteCommand


class CleanArea(ExecuteCommand):
    """Clean area command."""

    NAME = "Clean"
    HAS_SUB_ELEMENT = True

    def __init__(self, mode: CleanMode, area: str, cleanings: int = 1) -> None:
        # <ctl><clean type='SpotArea' act='s' speed='standard' deep='1' mid='4,5'/></ctl>

        super().__init__(
            {
                "type": mode.xml_value,
                "act": CleanAction.START.xml_value,
                "speed": "standard",  # TODO: FanSpeedLevel.NORMAL.xml_value, after #560 is merged
                "deep": str(cleanings),
                "mid": area,
            }
        )
