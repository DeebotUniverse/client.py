"""China T80-specific work-state message handling."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.events.auto_empty import Frequency
from deebot_client.events.station import StationEvent
from deebot_client.events.xwk78e import (
    AutoEmptyEventT80,
    AutoEmptyIntensity,
    WashMode,
    WashModeEvent,
)
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.messages.json.work_state import _WORK_STATE_2_EVENTS
from deebot_client.models import State as RobotState

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnWorkStateT80(MessageBodyDataDict):
    """Handle T80's stale paused payloads without changing other models."""

    NAME = "onWorkState"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        robot_state = data.get("robotState", {}).get("state")
        station_state = data.get("stationState", {}).get("state")
        robot_status, station_status = _WORK_STATE_2_EVENTS.get(robot_state, {}).get(
            station_state, (None, None)
        )

        if (robot_status, station_status) == (None, None):
            return HandlingResult.analyse()

        if data.get("paused") == 1:
            robot_data = data.get("robotState", {})
            voice_charging = (
                robot_data.get("state") == "cleaning"
                and robot_data.get("trigger") == "voice"
                and station_state == "idle"
            )
            last_state = event_bus.get_last_event(StateEvent)
            if voice_charging or (
                last_state and last_state.state == RobotState.DOCKED
            ):
                robot_status = None
            else:
                robot_status = RobotState.PAUSED

        if robot_status is not None:
            event_bus.notify(StateEvent(robot_status))
        if station_status is not None:
            event_bus.notify(StationEvent(station_status))

        return HandlingResult.success()


class OnAutoEmptyT80(MessageBodyDataDict):
    """Parse T80 auto-empty state including suction intensity."""

    NAME = "onAutoEmpty"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        frequency = None
        if frequency_value := data.get("frequency"):
            frequency = Frequency(frequency_value)
        intensity = data.get("intensity")
        event_bus.notify(
            AutoEmptyEventT80(
                bool(data["enable"]),
                frequency,
                AutoEmptyIntensity(intensity) if intensity is not None else None,
            )
        )
        return HandlingResult.success()


class OnWashInfoT80(MessageBodyDataDict):
    """Parse T80 station mop-washing mode state."""

    NAME = "onWashInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        try:
            mode = WashMode(data["mode"])
        except (KeyError, ValueError):
            return HandlingResult.analyse()
        event_bus.notify(WashModeEvent(mode, data.get("interval")))
        return HandlingResult.success()
