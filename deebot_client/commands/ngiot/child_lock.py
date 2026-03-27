"""Child lock commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import ChildLockEvent
from deebot_client.message import HandlingResult, HandlingState

from .common import RobotDetailGetCommand, RobotDetailSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetChildLock(RobotDetailGetCommand):
    """Get child-lock state from the robot-detail surface."""

    NAME = "getChildLock"
    FIELDS = ("childLock",)

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus: EventBus,
        data: dict[str, Any],
    ) -> HandlingResult:
        event_bus.notify(ChildLockEvent(bool(data.get("childLock"))))
        return HandlingResult.success()


class SetChildLock(RobotDetailSetCommand):
    """Set child-lock state on the robot-detail surface."""

    NAME = "setChildLock"
    get_command = GetChildLock

    def __init__(self, enable: bool) -> None:
        super().__init__({"childLock": bool(enable)})
        self._enable = bool(enable)

    def _get_body_data(self) -> dict[str, Any]:
        return {"childLock": self._enable}

    def _handle_response(
        self,
        event_bus: EventBus,
        response: dict[str, Any],
    ) -> HandlingResult:
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.notify(ChildLockEvent(self._enable))
        return result