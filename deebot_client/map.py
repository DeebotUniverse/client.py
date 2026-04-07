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

        Extra-safe behavior:
        - legacy trace/icon/position behavior remains the default
        - NGIOT trace and position transforms are enabled only when a valid
          NGIOT raster background is actively applied
        - legacy devices keep the existing transform path
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
                # Extra-safe rule:
                # - if NGIOT background is active, keep world-space trace scaling
                # - otherwise fall back to legacy scaling
                if self._map_data.has_ngiot_background():
                    self._map_data.use_world_trace_scale()
                else:
                    self._map_data.use_legacy_trace_scale()

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
            self._map_data.use_legacy_trace_scale()
            self._map_data.use_legacy_position_icon_scale()
            self._map_data.use_legacy_position_transform()
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
            self._map_data.use_legacy_trace_scale()
            self._map_data.use_legacy_position_icon_scale()
            self._map_data.use_legacy_position_transform()
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
            direction=int(getattr(base_map, "direction", 0)),
        )
        self._map_data.use_world_trace_scale()
        self._map_data.use_ngiot_position_icon_scale()
        # eyfj07 position payloads are already in world/map coordinates.
        # Do not re-offset them by xMin/yMax here.
        self._map_data.use_legacy_position_transform()


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

        # Extra-safe defaults for backward compatibility.
        self.use_legacy_trace_scale()
        self.use_legacy_position_icon_scale()
        self.use_legacy_position_transform()

    @property
    def changed(self) -> bool:
        """Indicate if data was changed."""
        return self._changed

    @property
    def map_subsets(self) -> OnChangedDict[tuple[str, int], MapSubsetEvent]:
        """Map subsets."""
        return self._map_subsets

    def reset_changed(self) -> None:
        """Reset changed state."""
        self._changed = False

    def teardown(self) -> None:
        """Teardown map data."""
        self._room_handling.teardown()

    def update_positions(self, positions: list[Position]) -> None:
        """Update positions."""
        if self._positions != positions:
            self._positions = positions
            self._on_change()

    def set_rotation_angle(self, angle: int | RotationAngle) -> None:
        """Set rotation angle."""
        if isinstance(angle, RotationAngle):
            new_rotation = angle
        else:
            angle_mapping = {
                0: RotationAngle.DEG_0,
                90: RotationAngle.DEG_90,
                180: RotationAngle.DEG_180,
                270: RotationAngle.DEG_270,
            }
            new_rotation = angle_mapping.get(int(angle) % 360, RotationAngle.DEG_0)

        if self._rotation != new_rotation:
            self._rotation = new_rotation
            self._on_change()

    def set_map_info(self, map_info: list[str]) -> None:
        """Set map info."""
        self._data.set_map_info(map_info)
        self._on_change()

    def set_background_image(self, image: str) -> None:
        """Set background image."""
        self._data.set_background_image(image)
        self._on_change()

    def clear_background_image(self) -> None:
        """Clear background image."""
        self._data.clear_background_image()
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
        direction: int,
    ) -> None:
        """Set NGIOT raster background."""
        self._data.set_ngiot_background(
            encoded=encoded,
            width=width,
            height=height,
            total_width=total_width,
            total_height=total_height,
            resolution=resolution,
            x_min=x_min,
            y_max=y_max,
            direction=direction,
        )
        self._on_change()

    def clear_ngiot_background(self) -> None:
        """Clear NGIOT raster background."""
        self._data.clear_ngiot_background()
        self._on_change()

    def has_ngiot_background(self) -> bool:
        """Return True when an NGIOT raster background is active."""
        return self._data.has_ngiot_background()

    def use_legacy_trace_scale(self) -> None:
        """Use legacy trace scaling."""
        self._data.use_legacy_trace_scale()

    def use_world_trace_scale(self) -> None:
        """Use world-space trace scaling."""
        self._data.use_world_trace_scale()

    def use_legacy_position_icon_scale(self) -> None:
        """Use legacy position icon scale."""
        self._data.use_legacy_position_icon_scale()

    def use_ngiot_position_icon_scale(self) -> None:
        """Use NGIOT position icon scale."""
        self._data.use_ngiot_position_icon_scale()

    def use_legacy_position_transform(self) -> None:
        """Use legacy position transform."""
        self._data.use_legacy_position_transform()

    def use_ngiot_position_transform(self) -> None:
        """Use NGIOT position transform."""
        self._data.use_ngiot_position_transform()

    def clear_trace_points(self) -> None:
        """Clear trace points."""
        self._data.clear_trace_points()
        self._on_change()

    def add_trace_points(self, data: str, lz4_len: int | None = None) -> None:
        """Add trace points."""
        self._data.add_trace_points(data, lz4_len)
        self._on_change()

    def generate_svg(self) -> str | None:
        """Generate SVG."""
        map_subsets = list(self.map_subsets.values())
        self._room_handling.update_rooms(map_subsets)
        return self._data.generate_svg(
            map_subsets,
            self._positions,
            self._rotation,
        )


class MapRoomHandling:
    """Handle room data."""

    def __init__(self, event_bus: EventBus, on_change: Callable[[], None]) -> None:
        self._event_bus = event_bus
        self._on_change = on_change
        self._room_names: dict[int, Room] = {}

        async def on_rooms(event: RoomsEvent) -> None:
            if self._room_names != event.rooms:
                self._room_names = event.rooms
                self._on_change()

        self._unsubscribe = event_bus.subscribe(RoomsEvent, on_rooms)

    def teardown(self) -> None:
        """Teardown room handling."""
        self._unsubscribe()

    def update_rooms(self, map_subsets: list[MapSubsetEvent]) -> None:
        """Update rooms."""
        for subset in map_subsets:
            if subset.type == MapSetType.Vacuum:
                if room := self._room_names.get(subset.id):
                    subset.name = room.name