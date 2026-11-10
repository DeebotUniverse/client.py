"""Base station messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.events.station import State, StationEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State as RobotState

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
        # "body":{"data":{"content":{"error":[],"type":2,"motionState":1},"state":1},"code":0,"msg":"ok"} - Drying mop
        #
        # X2 OMNI reports station state=0 while mop washing is active.
        # Preserve WASHING_MOP when clean info has already reported washing
        # and the robot itself is still cleaning.

        if (state := data.get("state")) == 0:
            last_station_event = event_bus.get_last_event(StationEvent)
            last_robot_event = event_bus.get_last_event(StateEvent)

            if (
                last_station_event
                and last_station_event.state == State.WASHING_MOP
                and last_robot_event
                and last_robot_event.state == RobotState.CLEANING
            ):
                reported_state = State.WASHING_MOP
            else:
                reported_state = State.IDLE
        elif (
            state == 1
            and (content := data.get("content"))
            and content.get("type") == 1
            and content.get("motionState") == 1
        ):
            reported_state = State.EMPTYING_DUSTBIN
        elif (
            state == 1
            and (content := data.get("content"))
            and content.get("type") == 2
            and content.get("motionState") == 1
        ):
            reported_state = State.DRYING_MOP
        else:
            return HandlingResult.analyse()

        event_bus.notify(StationEvent(reported_state))
        return HandlingResult.success()
