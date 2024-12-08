"""Charge commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.logging_filter import get_logger

from .common import ExecuteCommand

if TYPE_CHECKING:
    from deebot_client.events import BaseStationAction

_LOGGER = get_logger(__name__)


class StationAction(ExecuteCommand):
    """Station Action command."""

    name = "stationAction"

    def __init__(self, action: BaseStationAction) -> None:
        super().__init__({"act": 1, "type": action.value})
