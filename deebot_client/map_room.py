"""Map room handling module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import (
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    RoomsEvent,
)
from deebot_client.models import Room
from deebot_client.util import OnChangedDict

if TYPE_CHECKING:
    from collections.abc import Callable

    from deebot_client.event_bus import EventBus


class MapRoomHandling:
    """Room handling."""

    def __init__(self, event_bus: EventBus, on_change: Callable[[], None]) -> None:
        self._amount_rooms: int = 0
        self._rooms: OnChangedDict[int, Room] = OnChangedDict(on_change)
        self._unsubscribers: list[Callable[[], None]] = []
        self._map_id: str = ""

        async def on_map_set(event: MapSetEvent) -> None:
            if event.type != MapSetType.ROOMS:
                return

            self._map_id = event.map_id
            self._amount_rooms = len(event.subsets)
            for room_id in self._rooms.copy():
                if room_id not in event.subsets:
                    self._rooms.pop(room_id, None)

        self._unsubscribers.append(event_bus.subscribe(MapSetEvent, on_map_set))

        async def on_map_subset(event: MapSubsetEvent) -> None:
            if event.type != MapSetType.ROOMS or not event.name:
                return

            room = Room(event.name, event.id, event.coordinates)
            if self._rooms.get(event.id, None) != room:
                self._rooms[room.id] = room

                if len(self._rooms) == self._amount_rooms:
                    event_bus.notify(
                        RoomsEvent(self._map_id, list(self._rooms.values()))
                    )

        self._unsubscribers.append(event_bus.subscribe(MapSubsetEvent, on_map_subset))

    def clear(self) -> None:
        """Clear cached rooms without unsubscribing."""
        self._amount_rooms = 0
        self._rooms.clear()
        self._map_id = ""

    def teardown(self) -> None:
        """Teardown room handling."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
