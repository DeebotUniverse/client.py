from __future__ import annotations

from deebot_client.capabilities import (
    CapabilityEvent,
    CapabilityExecuteTypes,
    CapabilitySetTypes,
    CapabilityStation,
    _get_events,
)
from deebot_client.commands import StationAction
from deebot_client.commands.json.auto_empty import GetAutoEmpty, SetAutoEmpty
from deebot_client.commands.json.station_action import (
    StationAction as StationActionCommand,
)
from deebot_client.commands.json.station_state import GetStationState
from deebot_client.events import (
    AutoEmptyEvent,
    StationErrorEvent,
    StationEvent,
    auto_empty,
)


def test_station_error_event_is_refreshable() -> None:
    """Registering StationErrorEvent under CapabilityStation wires a refresh."""
    station = CapabilityStation(
        action=CapabilityExecuteTypes(
            StationActionCommand,
            types=(StationAction.EMPTY_DUSTBIN,),
        ),
        auto_empty=CapabilitySetTypes(
            event=AutoEmptyEvent,
            get=[GetAutoEmpty()],
            set=SetAutoEmpty,
            types=(auto_empty.Frequency.AUTO,),
        ),
        state=CapabilityEvent(StationEvent, [GetStationState()]),
        error=CapabilityEvent(StationErrorEvent, [GetStationState()]),
    )

    events = _get_events(station)

    assert events[StationEvent] == [GetStationState()]
    assert events[StationErrorEvent] == [GetStationState()]
