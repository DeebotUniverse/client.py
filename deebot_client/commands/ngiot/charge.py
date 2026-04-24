"""Charge commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import State
from deebot_client.ngiot_client import NgiotRequest

from .common import APN_RETURN_TO_DOCK, NgiotExecuteCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo
    from deebot_client.ngiot_client import NgiotClient


class Charge(NgiotExecuteCommand):
    """Return robot to charge dock."""

    NAME = "charge"

    def __init__(self) -> None:
        super().__init__({})

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        return await client.request(
            device_info,
            NgiotRequest(
                apn=APN_RETURN_TO_DOCK,
                body_data={"chargeSwitch": True},
            ),
        )

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        result = super()._handle_body(event_bus, body)
        if result.state == HandlingState.SUCCESS:
            event_bus.notify(StateEvent(State.RETURNING))
        return result