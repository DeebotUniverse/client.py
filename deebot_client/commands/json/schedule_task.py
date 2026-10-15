"""Schedule task commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .common import ExecuteCommand

if TYPE_CHECKING:
    from deebot_client.models import CleanAction


class SetScheduleTask(ExecuteCommand):
    """Pause or resume the running scheduled task (mowers)."""

    NAME = "setScheduleTask"

    def __init__(self, action: CleanAction) -> None:
        super().__init__({"act": action.value})
