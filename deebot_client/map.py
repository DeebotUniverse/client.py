"""Map module."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

from deebot_client.events.map import CachedMapInfoEvent, MajorMapEvent, MapChangedEvent

from .events import (
    MapInfoEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    Position,
    PositionsEvent,
    RoomsEvent,
)
from .exceptions import MapError
from .logging_filter import get_logger
from .models import Room
from .rs.map import MapData as MapDataRs, RotationAngle
from .util import OnChangedDict

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
            for subset_key, subset in self._map_data.map_subsets.copy().items():
                if subset.type == event.type and subset.id not in event.subsets:
                    self._map_data.map_subsets.pop(subset_key, None)

        self._unsubscribers.append(event_bus.subscribe(MapSetEvent, on_map_set))

        async def on_map_subset(event: MapSubsetEvent) -> None:
            subset_key = (str(event.type), event.id)
            if self._map_data.map_subsets.get(subset_key, None) != event:
                self._map_data.map_subsets[subset_key] = event

        self._unsubscribers.append(event_bus.subscribe(MapSubsetEvent, on_map_subset))

        self._unsubscribers.append(
            event_bus.add_on_subscription_callback(
                MapChangedEvent, self._on_first_map_changed_subscription
            )
        )

        async def on_map_info(event: MapInfoEvent) -> None:
            self._map_data.set_map_info(event.info)

        self._unsubscribers.append(event_bus.subscribe(MapInfoEvent, on_map_info))

    async def _on_first_map_changed_subscription(self) -> Callable[[], None]:
        """On first MapChanged subscription.

        For NGIOT devices, the visible base map comes from the raster payload stored
        in the NGIOT map state store. This callback wires the Python map layer to
        that store and keeps overlays layered on top.
        """
        unsubscribers: list[Callable[[], None]] = []

        async def on_cached_info(event: CachedMapInfoEvent) -> None:
            used_map = next((m for m in event.maps if m.using), None)
            if used_map:
                self._map_data.set_rotation_angle(used_map.angle)
            self._sync_ngiot_background_from_store()

        cached_map_subscribers = self._event_bus.has_subscribers(CachedMapInfoEvent)
        unsubscribers.append(
            self._event_bus.subscribe(CachedMapInfoEvent, on_cached_info)
        )
        if cached_map_subscribers:
            self._event_bus.request_refresh(CachedMapInfoEvent)

        async def on_major_map(_: MajorMapEvent) -> None:
            self._sync_ngiot_background_from_store()

        unsubscribers.append(self._event_bus.subscribe(MajorMapEvent, on_major_map))

        async def on_position(event: PositionsEvent) -> None:
            self._map_data.update_positions(event.positions)
            self._sync_ngiot_background_from_store()

        unsubscribers.append(self._event_bus.subscribe(PositionsEvent, on_position))

        async def on_map_trace(event: MapTraceEvent) -> None:
            if event.start == 0:
                self._map_data.clear_trace_points()

            if not (data := event.data.strip()):
                return

            try:
                self._map_data.add_trace_points(data, event.lz4_len)
            except ValueError as err:
                _LOGGER.warning(
                    "Skipping invalid trace payload for geometry map "
                    "(start=%s total=%s lz4_len=%s): %s",
                    event.start,
                    event.total,
                    event.lz4_len,
                    err,
                )
            except Exception:
                _LOGGER.exception(
                    "Unexpected error while processing trace payload; continuing without trace"
                )

        unsubscribers.append(self._event_bus.subscribe(MapTraceEvent, on_map_trace))

        self._sync_ngiot_background_from_store()

        def unsub() -> None:
            for unsubscribe in unsubscribers:
                unsubscribe()

        return unsub

    def refresh(self) -> None:
        """Manually refresh map."""
        if not self._unsubscribers:
            raise MapError("Please enable the map first")

        self._event_bus.request_refresh(CachedMapInfoEvent)
        self._event_bus.request_refresh(MajorMapEvent)
        self._event_bus.request_refresh(PositionsEvent)
        self._event_bus.request_refresh(MapTraceEvent)

    def get_svg_map(self) -> str | None:
        """Return map as SVG string."""
        if not self._unsubscribers:
            raise MapError("Please enable the map first")

        if self._last_image and not self._map_data.changed:
            _LOGGER.debug("[get_svg_map] No need to update")
            return self._last_image

        _LOGGER.debug("[get_svg_map] Begin")

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

    def _sync_ngiot_background_from_store(self) -> None:
        """Push the active NGIOT raster background into the renderer path."""
        store = getattr(self._event_bus, "_ngiot_map_state_store", None)
        if store is None:
            self._map_data.clear_ngiot_background()
            return

        snapshot = None
        get_active_renderable = getattr(store, "get_active_renderable", None)
        if callable(get_active_renderable):
            snapshot = get_active_renderable()

        if snapshot is None:
            get_active = getattr(store, "get_active", None)
            if callable(get_active):
                snapshot = get_active()

        base_map = getattr(snapshot, "base_map", None) if snapshot is not None else None
        encoded = ""
        if base_map is not None:
            encoded = getattr(base_map, "encoded", "") or getattr(base_map, "data", "")

        if (
            base_map is None
            or not encoded
            or int(getattr(base_map, "width", 0)) <= 0
            or int(getattr(base_map, "height", 0)) <= 0
        ):
            self._map_data.clear_ngiot_background()
            return

        self._map_data.set_ngiot_background(
            encoded=encoded,
            width=int(getattr(base_map, "width", 0)),
            height=int(getattr(base_map, "height", 0)),
            total_width=int(getattr(base_map, "total_width", 0)),
            total_height=int(getattr(base_map, "total_height", 0)),
            resolution=int(getattr(base_map, "resolution", 1)),
            x_min=int(getattr(base_map, "x_min", 0)),
            y_max=int(getattr(base_map, "y_max", 0)),
        )


class MapData:
    """Map data."""

    def __init__(self, event_bus: EventBus) -> None:
        self._changed: bool = False

        def on_change() -> None:
            self._changed = True
            event_bus.notify(MapChangedEvent(datetime.now(UTC)), debounce_time=1)

        self._on_change = on_change
        self._map_subsets: OnChangedDict[tuple[str, int], MapSubsetEvent] = (
            OnChangedDict(on_change)
        )
        self._positions: list[Position] = []
        self._rotation: RotationAngle = RotationAngle.DEG_0
        self._data = MapDataRs()
        self._room_handling = MapRoomHandling(event_bus, on_change)

    @property
    def changed(self) -> bool:
        """Indicate if data was changed."""
        return self._changed

    @property
    def map_subsets(self) -> dict[tuple[str, int], MapSubsetEvent]:
        """Return map subsets."""
        return self._map_subsets

    def reset_changed(self) -> None:
        """Reset changed value."""
        self._changed = False

    def add_trace_points(self, value: str, lz4_len: int | None = None) -> None:
        """Add trace points to the map data."""
        self._data.trace_points.add(value, lz4_len)
        self._on_change()

    def clear_trace_points(self) -> None:
        """Clear trace points."""
        self._data.trace_points.clear()
        self._on_change()

    def update_positions(self, value: list[Position]) -> None:
        """Merge partial position updates by type."""

        def _position_key(position: Position) -> str:
            return str(position.type)

        merged: dict[str, Position] = {
            _position_key(position): position for position in self._positions
        }

        for position in value:
            merged[_position_key(position)] = position

        new_positions = list(merged.values())
        if new_positions != self._positions:
            self._positions = new_positions
            self._on_change()

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
        if self._rotation != rotation:
            self._rotation = rotation
            self._on_change()

    def set_ngiot_background(
        self,
        *,
        encoded: str,
        width: int,
        height: int,
        total_width: int,
        total_height: int,
        resolution: int,
        x_min: int,
        y_max: int,
    ) -> None:
        """Set the active NGIOT raster background payload."""
        if self._data.ngiot_background.set_map_data(
            encoded,
            width,
            height,
            total_width,
            total_height,
            resolution,
            x_min,
            y_max,
        ):
            self._on_change()

    def clear_ngiot_background(self) -> None:
        """Clear the active NGIOT raster background payload."""
        if self._data.ngiot_background.clear():
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