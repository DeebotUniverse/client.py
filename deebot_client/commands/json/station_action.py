"""Charge commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .common import ExecuteCommand

if TYPE_CHECKING:
    from deebot_client import commands


class StationAction(ExecuteCommand):
    """Station Action command."""

    NAME = "stationAction"

    def __init__(self, action: commands.StationAction) -> None:
        super().__init__({"act": 1, "type": action.value})
