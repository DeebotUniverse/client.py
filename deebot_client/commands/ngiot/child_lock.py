"""Child lock commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import ChildLockEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.ngiot_client import APN_CHILD_LOCK

from .common import NgiotExecuteCommand, RobotDetailGetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo
    from deebot_client.ngiot_client import NgiotClient


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


class SetChildLock(NgiotExecuteCommand):
    """Set child-lock state using the confirmed NGIOT write APN."""

    NAME = "setChildLock"
    get_command = GetChildLock

    def __init__(self, enable: bool) -> None:
        super().__init__({})
        self._enable = bool(enable)

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        return await client.request(
            device_info,
            apn=APN_CHILD_LOCK,
            body_data={"childLock": self._enable},
        )

    def _handle_response(
        self,
        event_bus: EventBus,
        response: dict[str, Any],
    ) -> HandlingResult:
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.notify(ChildLockEvent(self._enable))
        return result