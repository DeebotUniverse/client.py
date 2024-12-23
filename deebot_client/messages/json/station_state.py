"""Base station messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.station import State, StationEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnStationState(MessageBodyDataDict):
    """On battery message."""

    NAME = "onStationState"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # "body":{"data":{"content":{"error":[],"type":0},"state":0},"code":0,"msg":"ok"} - Idle
        # "body":{"data":{"content":{"error":[],"type":1,"motionState":1},"state":1},"code":0,"msg":"ok"} - Emptying

        if (state := data.get("state")) == 0:
            reported_state = State.IDLE
        elif (
            state == 1
            and (content := data.get("content"))
            and content.get("type") == 1
            and content.get("motionState") == 1
        ):
            reported_state = State.EMPTYING
        else:
            return HandlingResult.analyse()

        event_bus.notify(StationEvent(reported_state))
        return HandlingResult.success()
