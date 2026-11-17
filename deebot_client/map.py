"""Map module."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

from deebot_client.events.map import CachedMapInfoEvent, MapChangedEvent

from .events import (
    Furniture,
    FurnitureEvent,
    MajorMapEvent,
    MapInfoEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
    Position,
    PositionsEvent,
    RoomsEvent,
)
from .exceptions import MapError
from .logging_filter import get_logger
from .models import Room
from .rs.map import MapData as MapDataRs, RotationAngle
from .util import (
    OnChangedDict,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .capabilities import CapabilityMap
    from .device import DeviceCommandExecute
    from .event_bus import EventBus

_LOGGER = get_logger(__name__)


class Map:
    """Map representation."""

    def __init__(
        self,
        execute_command: DeviceCommandExecute,
        event_bus: EventBus,
        capabilities: CapabilityMap,
    ) -> None:
        self._execute_command = execute_command
        self._event_bus = event_bus

        self._capabilities = capabilities
        self._map_data: Final[MapData] = MapData(event_bus)
        self._last_image: str | None = None
        self._unsubscribers: list[Callable[[], None]] = []

        async def on_map_set(event: MapSetEvent) -> None:
            for subset_id, subset in self._map_data.map_subsets.copy().items():
                if subset.type == event.type and subset_id not in event.subsets:
                    self._map_data.map_subsets.pop(subset_id, None)

        self._unsubscribers.append(event_bus.subscribe(MapSetEvent, on_map_set))

        async def on_map_subset(event: MapSubsetEvent) -> None:
            if (
                event.type != MapSetType.ROOMS
                and self._map_data.map_subsets.get(event.id, None) != event
            ):
                self._map_data.map_subsets[event.id] = event

        self._unsubscribers.append(event_bus.subscribe(MapSubsetEvent, on_map_subset))

        self._unsubscribers.append(
            event_bus.add_on_subscription_callback(
                MapChangedEvent, self._on_first_map_changed_subscription
            )
        )

        async def on_map_info(event: MapInfoEvent) -> None:
            self._map_data.set_map_info(event.info)

        self._unsubscribers.append(event_bus.subscribe(MapInfoEvent, on_map_info))

        async def on_furniture(event: FurnitureEvent) -> None:
            self._map_data.set_furniture(event.map_id, event.furniture)

        self._unsubscribers.append(event_bus.subscribe(FurnitureEvent, on_furniture))

    # ---------------------------- METHODS ----------------------------

    async def _subscribe_minor_major_map_events(self) -> list[Callable[[], None]]:
        if (minor := self._capabilities.minor) is None:
            # Device sends the whole map outline in the MapInfo_V2 message and
            # doesn't support requesting it piece by piece.
            return []

        async def on_major_map(event: MajorMapEvent) -> None:
            async with asyncio.TaskGroup() as tg:
                for idx, value in enumerate(event.values):
                    if (
                        self._map_data.map_piece_crc32_indicates_update(idx, value)
                        and event.requested
                    ):
                        tg.create_task(
                            self._execute_command(minor.execute(idx, event.map_id))
                        )

        async def on_minor_map(event: MinorMapEvent) -> None:
            self._map_data.update_map_piece(event.index, event.value)

        return [
            self._event_bus.subscribe(MajorMapEvent, on_major_map),
            self._event_bus.subscribe(MinorMapEvent, on_minor_map),
        ]

    async def _on_first_map_changed_subscription(self) -> Callable[[], None]:
        """On first MapChanged subscription."""
        unsubscribers = await self._subscribe_minor_major_map_events()

        async def on_cached_info(event: CachedMapInfoEvent) -> None:
            used_map = next((m for m in event.maps if m.using), None)
            self._map_data.set_active_map(used_map.id if used_map else None)
            if used_map:
                self._map_data.set_rotation_angle(used_map.angle)

        cached_map_subscribers = self._event_bus.has_subscribers(CachedMapInfoEvent)
        unsubscribers.append(
            self._event_bus.subscribe(CachedMapInfoEvent, on_cached_info)
        )
        if cached_map_subscribers:
            # Request update only if there was already a subscriber before
            self._event_bus.request_refresh(CachedMapInfoEvent)

        async def on_position(event: PositionsEvent) -> None:
            self._map_data.update_positions(event.positions)

        unsubscribers.append(self._event_bus.subscribe(PositionsEvent, on_position))

        async def on_map_trace(event: MapTraceEvent) -> None:
            if event.start == 0:
                self._map_data.clear_trace_points()

            if data := event.data.strip():
                self._map_data.add_trace_points(data)

        unsubscribers.append(self._event_bus.subscribe(MapTraceEvent, on_map_trace))

        async def on_rooms(event: RoomsEvent) -> None:
            self._map_data.set_rooms(event.map_id, event.rooms)

        unsubscribers.append(self._event_bus.subscribe(RoomsEvent, on_rooms))

        def unsub() -> None:
            for unsub in unsubscribers:
                unsub()

        return unsub

    def refresh(self) -> None:
        """Manually refresh map."""
        if not self._unsubscribers:
            raise MapError("Please enable the map first")

        # TODO make it nice
        # CachedMapInfoEvent also triggers MapInfo_V2, which carries the map
        # outline for devices without major/minor map support.
        self._event_bus.request_refresh(CachedMapInfoEvent)
        self._event_bus.request_refresh(PositionsEvent)
        self._event_bus.request_refresh(MapTraceEvent)
        if self._capabilities.major is not None:
            self._event_bus.request_refresh(MajorMapEvent)

    def get_svg_map(self) -> str | None:
        """Return map as SVG string."""
        if not self._unsubscribers:
            raise MapError("Please enable the map first")

        if self._last_image and not self._map_data.changed:
            _LOGGER.debug("[get_svg_map] No need to update")
            return self._last_image

        _LOGGER.debug("[get_svg_map] Begin")

        # Reset change before starting to build the SVG
        self._map_data.reset_changed()

        self._last_image = self._map_data.generate_svg()
        _LOGGER.debug("[get_svg_map] Finish")
        return self._last_image

    async def teardown(self) -> None:
        """Teardown map."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        self._map_data.teardown()


class MapData:
    """Map data."""

    def __init__(self, event_bus: EventBus) -> None:
        self._changed: bool = False

        def on_change() -> None:
            self._changed = True
            event_bus.notify(MapChangedEvent(datetime.now(UTC)), debounce_time=1)

        self._on_change = on_change
        self._map_subsets: OnChangedDict[int, MapSubsetEvent] = OnChangedDict(on_change)
        self._positions: list[Position] = []
        # Rooms and furniture belong to a map and the bot can also send them for
        # maps, which are not in use. Only the ones of the active map are drawn.
        self._active_map_id: str | None = None
        self._latest_map_id: str | None = None
        self._rooms: dict[str, list[Room]] = {}
        self._furniture: dict[str, list[Furniture]] = {}
        self._rotation: RotationAngle = RotationAngle.DEG_0
        self._data = MapDataRs()
        self._room_handling = MapRoomHandling(event_bus, on_change)

    @property
    def changed(self) -> bool:
        """Indicate if data was changed."""
        return self._changed

    @property
    def map_subsets(self) -> dict[int, MapSubsetEvent]:
        """Return map subsets."""
        return self._map_subsets

    def reset_changed(self) -> None:
        """Reset changed value."""
        self._changed = False

    def add_trace_points(self, value: str) -> None:
        """Add trace points to the map data."""
        self._data.trace_points.add(value)
        self._on_change()

    def clear_trace_points(self) -> None:
        """Clear trace points."""
        self._data.trace_points.clear()
        self._on_change()

    def update_positions(self, value: list[Position]) -> None:
        """Update positions."""
        self._positions = value
        self._on_change()

    def update_map_piece(self, index: int, base64_data: str) -> None:
        """Update map piece."""
        if self._data.background_image.update_map_piece(index, base64_data):
            self._on_change()

    def map_piece_crc32_indicates_update(self, index: int, crc32: int) -> bool:
        """Return True if update is required."""
        return self._data.background_image.map_piece_crc32_indicates_update(
            index, crc32
        )

    def generate_svg(self) -> str | None:
        """Generate SVG image."""
        map_id = self._drawn_map_id
        return self._data.generate_svg(
            # Sorted, so the image does not depend on the order they were received
            sorted(self._map_subsets.values(), key=lambda subset: subset.id),
            self._positions,
            self._rotation,
            self._rooms.get(map_id, []) if map_id else [],
            self._furniture.get(map_id, []) if map_id else [],
        )

    def set_map_info(self, base64_info: str) -> None:
        """Set compressed map info (parsing happens in Rust)."""
        self._data.map_info.set(base64_info)
        self._on_change()

    @property
    def _drawn_map_id(self) -> str | None:
        """Return the id of the map, which rooms and furniture are drawn.

        Until the active map is known, the map of the latest update is used.
        """
        return self._active_map_id or self._latest_map_id

    def _on_map_data_change(self, map_id: str) -> None:
        """Mark the image as changed, if the given map is the drawn one."""
        self._latest_map_id = map_id
        if map_id == self._drawn_map_id:
            self._on_change()

    def set_active_map(self, map_id: str | None) -> None:
        """Set the map, which is in use, or None if no map is in use."""
        if map_id != self._active_map_id:
            self._active_map_id = map_id
            self._on_change()

    def set_rooms(self, map_id: str, rooms: list[Room]) -> None:
        """Set rooms of a map, which are used for the labels and the colors."""
        # Sorted, so the image does not depend on the order the rooms were received
        rooms = sorted(rooms, key=lambda room: room.id)
        if rooms != self._rooms.get(map_id):
            self._rooms[map_id] = rooms
            self._on_map_data_change(map_id)

    def set_furniture(self, map_id: str, furniture: list[Furniture]) -> None:
        """Set furniture of a map."""
        furniture = sorted(furniture, key=lambda item: item.id)
        if furniture != self._furniture.get(map_id):
            self._furniture[map_id] = furniture
            self._on_map_data_change(map_id)

    def set_rotation_angle(self, rotation: RotationAngle) -> None:
        """Set clockwise rotation angle for SVG image."""
        self._rotation = rotation
        self._on_change()

    def teardown(self) -> None:
        """Teardown map data."""
        self._room_handling.teardown()


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

            if self._rooms and event.map_id != self._map_id:
                # The known rooms are from another map
                self._rooms.clear()

            self._map_id = event.map_id
            self._amount_rooms = len(event.subsets)
            for room_id in self._rooms.copy():
                if room_id not in event.subsets:
                    self._rooms.pop(room_id, None)

            if len(self._rooms) == self._amount_rooms:
                # Rooms were removed (or there are none), so the remaining ones
                # are complete and no subset will follow
                event_bus.notify(RoomsEvent(self._map_id, list(self._rooms.values())))

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

    def teardown(self) -> None:
        """Teardown room handling."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
