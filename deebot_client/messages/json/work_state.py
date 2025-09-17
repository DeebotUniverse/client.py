"""Base work state messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.events.station import State as StationState, StationEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State as RobotState

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_WORK_STATE_2_EVENTS: dict[str, dict[str, tuple[RobotState | None, StationState]]] = {
    "idle": {
        "idle": (None, StationState.IDLE),
        "goCharging": (RobotState.RETURNING, StationState.IDLE),
        "goEmptying": (RobotState.RETURNING, StationState.IDLE),
        "emptying": (RobotState.DOCKED, StationState.EMPTYING_DUSTBIN),
        "washing": (RobotState.DOCKED, StationState.WASHING_MOP),
        "drying": (RobotState.DOCKED, StationState.DRYING_MOP),
    },
    "cleaning": {
        "idle": (RobotState.CLEANING, StationState.IDLE),
        "goCharging": (RobotState.RETURNING, StationState.IDLE),
        "goEmptying": (RobotState.RETURNING, StationState.IDLE),
        "emptying": (RobotState.DOCKED, StationState.EMPTYING_DUSTBIN),
        "washing": (RobotState.DOCKED, StationState.WASHING_MOP),
        "drying": (RobotState.DOCKED, StationState.DRYING_MOP),
    },
}


class OnWorkState(MessageBodyDataDict):
    """On work state message."""

    NAME = "onWorkState"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        robot_state = data.get("robotState", {}).get("state")
        station_state = data.get("stationState", {}).get("state")

        robot_status, station_status = _WORK_STATE_2_EVENTS.get(robot_state, {}).get(
            station_state, (None, None)
        )

        if (robot_status, station_status) == (None, None):
            return HandlingResult.analyse()

        if data.get("paused") == 1:
            robot_status = RobotState.PAUSED

        if robot_status is not None:
            event_bus.notify(StateEvent(robot_status))
        if station_status is not None:
            event_bus.notify(StationEvent(station_status))

        return HandlingResult.success()
