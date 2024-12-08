"""Base station messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import BaseStationEvent, BaseStationStatus
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnStationState(MessageBodyDataDict):
    """On battery message."""

    name = "onStationState"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # "body":{"data":{"content":{"error":[],"type":0},"state":0},"code":0,"msg":"ok"} - Idle
        # "body":{"data":{"content":{"error":[],"type":1,"motionState":1},"state":1},"code":0,"msg":"ok"} - Emptying
        # Assume anything else is possible

        if data.get("state") == 0:
            reported_state = BaseStationStatus.IDLE
        elif (
            data.get("content", {}).get("type") == 1
            and data["content"].get("motionState") == 1
        ):
            reported_state = BaseStationStatus.EMPTYING
        else:
            reported_state = BaseStationStatus.UNKNOWN

        event_bus.notify(BaseStationEvent(reported_state))
        return HandlingResult.success()
