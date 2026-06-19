"""Mow commands for GOAT A3000 LiDAR mower (cr0e4u).

This module contributes:

* :class:`CleanMowerArea` — zone/area mowing targeting a specific set of zone IDs
* :class:`GetMI` — triggers the mower to stream zone-map chunks via ``onMI``

:class:`CleanMower` (the auto-mow base command) lives in
:mod:`deebot_client.commands.json.clean` and is imported from there.

All payloads confirmed via traffic analysis of the Ecovacs GOAT A3000 (cr0e4u).
"""

from __future__ import annotations

from typing import Any

from deebot_client.commands.json.common import ExecuteCommand
from deebot_client.models import CleanAction, CleanMode

from .clean import CleanMower


class CleanMowerArea(CleanMower):
    """Zone / area mow command for GOAT mower devices.

    Extends :class:`CleanMower` to target a specific zone or set of zones::

        {"act": "start", "content": {"type": "spotArea", "value": "0,1"}}

    ``mode`` is typically ``CleanMode.SPOT_AREA`` for standard zone mowing.
    ``area`` is the list of integer zone IDs to mow (0-indexed).
    """

    def __init__(
        self,
        mode: CleanMode,
        area: list[int | float],
        _cleanings: int = 1,
    ) -> None:
        self._additional_content: dict[str, str] = {
            "type": mode.value,
            "value": ",".join(str(i) for i in area),
        }
        super().__init__(CleanAction.START)

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        args = super()._get_args(action)
        if action == CleanAction.START:
            args["content"].update(self._additional_content)
        return args


class GetMI(ExecuteCommand):
    """Request the mower to push zone-map chunks via ``onMI``.

    Sending ``getMI`` causes the robot to re-stream all ``onMI`` chunks
    from index 0, equivalent to what the Ecovacs app does on every connect.
    The resulting push messages are handled by :class:`OnMI` in
    ``deebot_client.messages.json.mow``.

    Confirmed via traffic analysis of the GOAT A3000 (cr0e4u):

    .. code-block:: json

        {"body": {"data": {"type": "ar"}}}

    Args:
        area_type: Map data type to request.
            ``"ar"`` — zone polygons (default, used for initial map load)
            ``"vw"`` — virtual walls
            ``"nc"`` — navigation coordinates
    """

    NAME = "getMI"

    def __init__(self, area_type: str = "ar") -> None:
        super().__init__({"type": area_type})
