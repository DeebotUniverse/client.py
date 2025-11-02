"""Map module."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

from deebot_client.events.map import CachedMapInfoEvent, MapChangedEvent

from .events import (
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
            if event.type == MapSetType.ROOMS:
                return

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

    # ---------------------------- METHODS ----------------------------

    async def _subscribe_minor_major_map_events(self) -> list[Callable[[], None]]:
        async def on_major_map(event: MajorMapEvent) -> None:
            async with asyncio.TaskGroup() as tg:
                for idx, value in enumerate(event.values):
                    if (
                        self._map_data.map_piece_crc32_indicates_update(idx, value)
                        and event.requested
                    ):
                        tg.create_task(
                            self._execute_command(
                                self._capabilities.minor.execute(idx, event.map_id)
                            )
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

        def unsub() -> None:
            for unsub in unsubscribers:
                unsub()

        return unsub

    def refresh(self) -> None:
        """Manually refresh map."""
        if not self._unsubscribers:
            raise MapError("Please enable the map first")

        # TODO make it nice
        self._event_bus.request_refresh(CachedMapInfoEvent)
        self._event_bus.request_refresh(PositionsEvent)
        self._event_bus.request_refresh(MapTraceEvent)
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
        return self._data.generate_svg(
            list(self._map_subsets.values()),
            self._positions,
            self._rotation,
        )

    def set_map_info(self, base64_info: str) -> None:
        """Set compressed map info (parsing happens in Rust)."""
        self._data.map_info.set(base64_info)
        self._on_change()

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

        async def on_map_set(event: MapSetEvent) -> None:
            if event.type != MapSetType.ROOMS:
                return

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
                    event_bus.notify(RoomsEvent(list(self._rooms.values())))

        self._unsubscribers.append(event_bus.subscribe(MapSubsetEvent, on_map_subset))

    def teardown(self) -> None:
        """Teardown room handling."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
