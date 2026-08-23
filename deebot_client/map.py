"""Map module."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

from deebot_client.events.map import (
    CachedMapInfoEvent,
    MapChangedEvent,
    MowerStaticMapEvent,
    MowerWorkAreasEvent,
)

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
        has_vacuum_map = any(
            capability is not None
            for capability in (
                capabilities.cached_info,
                capabilities.info,
                capabilities.major,
                capabilities.minor,
                capabilities.position,
                capabilities.rooms,
                capabilities.set,
                capabilities.trace,
            )
        )
        self._map_data: Final[MapData] = MapData(
            event_bus, enable_rooms=capabilities.rooms is not None
        )
        self._last_image: str | None = None
        self._unsubscribers: list[Callable[[], None]] = []

        if has_vacuum_map:
            self._subscribe_vacuum_map_events()

        self._unsubscribers.append(
            event_bus.add_on_subscription_callback(
                MapChangedEvent, self._on_first_map_changed_subscription
            )
        )

        if capabilities.mower is not None:
            self._subscribe_mower_map_events()

    def _subscribe_vacuum_map_events(self) -> None:
        """Subscribe to the legacy vacuum map snapshot events."""

        async def on_map_set(event: MapSetEvent) -> None:
            if event.type == MapSetType.ROOMS:
                return

            for subset_id, subset in self._map_data.map_subsets.copy().items():
                if subset.type == event.type and subset_id not in event.subsets:
                    self._map_data.map_subsets.pop(subset_id, None)

        self._unsubscribers.append(self._event_bus.subscribe(MapSetEvent, on_map_set))

        async def on_map_subset(event: MapSubsetEvent) -> None:
            if (
                event.type != MapSetType.ROOMS
                and self._map_data.map_subsets.get(event.id, None) != event
            ):
                self._map_data.map_subsets[event.id] = event

        self._unsubscribers.append(
            self._event_bus.subscribe(MapSubsetEvent, on_map_subset)
        )

        async def on_map_info(event: MapInfoEvent) -> None:
            self._map_data.set_map_info(event.info)

        self._unsubscribers.append(self._event_bus.subscribe(MapInfoEvent, on_map_info))

    def _subscribe_mower_map_events(self) -> None:
        """Subscribe to typed mower map snapshots."""

        async def on_mower_static_map(event: MowerStaticMapEvent) -> None:
            self._map_data.set_mower_static_map(event)

        self._unsubscribers.append(
            self._event_bus.subscribe(MowerStaticMapEvent, on_mower_static_map)
        )

        async def on_mower_work_areas(event: MowerWorkAreasEvent) -> None:
            self._map_data.set_mower_work_areas(event)

        self._unsubscribers.append(
            self._event_bus.subscribe(MowerWorkAreasEvent, on_mower_work_areas)
        )

    # ---------------------------- METHODS ----------------------------

    async def _subscribe_minor_major_map_events(self) -> list[Callable[[], None]]:
        minor = self._capabilities.minor
        if self._capabilities.major is None or minor is None:
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
            if used_map:
                self._map_data.set_rotation_angle(used_map.angle)

        if self._capabilities.cached_info is not None:
            cached_map_subscribers = self._event_bus.has_subscribers(CachedMapInfoEvent)
            unsubscribers.append(
                self._event_bus.subscribe(CachedMapInfoEvent, on_cached_info)
            )
            if cached_map_subscribers:
                # Request update only if there was already a subscriber before
                self._event_bus.request_refresh(CachedMapInfoEvent)

        async def on_position(event: PositionsEvent) -> None:
            self._map_data.update_positions(event.positions)

        if self._capabilities.position is not None:
            unsubscribers.append(self._event_bus.subscribe(PositionsEvent, on_position))

        async def on_map_trace(event: MapTraceEvent) -> None:
            if event.start == 0:
                self._map_data.clear_trace_points()

            if data := event.data.strip():
                self._map_data.add_trace_points(data)

        if self._capabilities.trace is not None:
            unsubscribers.append(self._event_bus.subscribe(MapTraceEvent, on_map_trace))

        def unsub() -> None:
            for unsub in unsubscribers:
                unsub()

        return unsub

    def refresh(self) -> None:
        """Manually refresh map."""
        if not self._unsubscribers:
            raise MapError("Please enable the map first")

        refresh_events = (
            self._capabilities.cached_info,
            self._capabilities.position,
            self._capabilities.trace,
            self._capabilities.major,
        )
        for capability in refresh_events:
            if capability is not None:
                self._event_bus.request_refresh(capability.event)

        if mower := self._capabilities.mower:
            self._event_bus.request_refresh(mower.static.event)
            self._event_bus.request_refresh(mower.work_areas.event)

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

    def __init__(self, event_bus: EventBus, *, enable_rooms: bool = True) -> None:
        self._changed: bool = False

        def on_change() -> None:
            self._changed = True
            event_bus.notify(MapChangedEvent(datetime.now(UTC)), debounce_time=1)

        self._on_change = on_change
        self._map_subsets: OnChangedDict[int, MapSubsetEvent] = OnChangedDict(on_change)
        self._positions: list[Position] = []
        self._rotation: RotationAngle = RotationAngle.DEG_0
        self._data = MapDataRs()
        self._mower_static_map: MowerStaticMapEvent | None = None
        self._mower_work_areas: dict[tuple[str, int], MowerWorkAreasEvent] = {}
        self._room_handling = (
            MapRoomHandling(event_bus, on_change) if enable_rooms else None
        )

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

    def set_mower_static_map(self, event: MowerStaticMapEvent) -> None:
        """Replace the current typed mower boundary snapshot."""
        work_areas = self._mower_work_areas.get((event.mid, event.step_size))
        changed = self._data.set_mower_map(event, work_areas)
        self._mower_static_map = event
        if changed:
            self._on_change()

    def set_mower_work_areas(self, event: MowerWorkAreasEvent) -> None:
        """Store a complete work-area snapshot and apply it only when compatible."""
        static_map = self._mower_static_map
        changed = False
        if (
            static_map is not None
            and static_map.mid == event.mid
            and static_map.step_size == event.step_size
        ):
            changed = self._data.set_mower_map(static_map, event)
        self._mower_work_areas[(event.mid, event.step_size)] = event
        if changed:
            self._on_change()

    def set_rotation_angle(self, rotation: RotationAngle) -> None:
        """Set clockwise rotation angle for SVG image."""
        self._rotation = rotation
        self._on_change()

    def teardown(self) -> None:
        """Teardown map data."""
        if self._room_handling is not None:
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

    def teardown(self) -> None:
        """Teardown room handling."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
