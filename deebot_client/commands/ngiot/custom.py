"""Custom NGIOT commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import CustomCommandEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.ngiot_client import NgiotRequest

from .common import NgiotRequestCommand

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from deebot_client.event_bus import EventBus


class CustomCommand(NgiotRequestCommand):
    """Send an arbitrary NGIOT endpoint-control request."""

    NAME = "customCommand"

    def __init__(
        self,
        apn: str | int,
        body_data: Mapping[str, Any] | Sequence[Any],
        *,
        fmt: str = "j",
        ct: str = "q",
    ) -> None:
        super().__init__(NgiotRequest(apn=apn, body_data=body_data, fmt=fmt, ct=ct))
        self._apn = str(apn)

    def _handle_response(
        self,
        event_bus: EventBus,
        response: dict[str, Any],
    ) -> HandlingResult:
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            body = response.get("resp", {}).get("body", {})
            event_bus.notify(CustomCommandEvent(name=self._apn, response=body))
        return result
