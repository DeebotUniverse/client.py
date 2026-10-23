"""Map data representation bridging Python events to Rust MapDataRs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from deebot_client.events.map import MapChangedEvent

from .map_room import MapRoomHandling
from .rs.map import MapData as MapDataRs, RotationAngle
from .util import OnChangedDict

if TYPE_CHECKING:
    from collections.abc import Callable

    from deebot_client.event_bus import EventBus
    from deebot_client.events import MapSetType, MapSubsetEvent, Position
    from deebot_client.events.map import NativeMapEvent


class MapData:
    """Map data."""

    def __init__(self, event_bus: EventBus) -> None:
        self._changed: bool = False

        def on_change() -> None:
            self._changed = True
            event_bus.notify(MapChangedEvent(datetime.now(UTC)), debounce_time=1)

        self._on_change: Callable[[], None] = on_change
        self._map_subsets: OnChangedDict[int, MapSubsetEvent] = OnChangedDict(on_change)
        self._native_map_subsets: OnChangedDict[
            tuple[MapSetType, int], MapSubsetEvent
        ] = OnChangedDict(on_change)
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
        """Return legacy map subsets keyed by their IDs."""
        return self._map_subsets

    @property
    def native_map_subsets(self) -> dict[tuple[MapSetType, int], MapSubsetEvent]:
        """Return native overlays without changing the legacy integer-key API."""
        return self._native_map_subsets

    def reset_changed(self) -> None:
        """Reset changed value."""
        self._changed = False

    def add_trace_points(self, value: str) -> None:
        """Add legacy trace points to the map data."""
        self._data.trace_points.add(value)
        self._on_change()

    def clear_trace_points(self) -> None:
        """Clear trace points."""
        self._data.trace_points.clear()
        self._on_change()

    def set_native_trace(
        self,
        base64_lz4: str | None,
        capacity: int,
        start: int,
        total: int,
    ) -> None:
        """Set native trace points from raw LZ4 chunk.

        Rust bridge is bundled; ValueError propagates for read-only recovery.
        """
        if self._data.trace_points.set_native(base64_lz4, capacity, start, total):
            self._on_change()

    def update_positions(self, value: list[Position]) -> None:
        """Update positions."""
        self._positions = value
        self._on_change()

    def update_map_piece(self, index: int, base64_data: str) -> None:
        """Update legacy map piece."""
        if self._data.background_image.update_map_piece(index, base64_data):
            self._on_change()

    def map_piece_crc32_indicates_update(self, index: int, crc32: int) -> bool:
        """Return True if update is required."""
        return self._data.background_image.map_piece_crc32_indicates_update(
            index, crc32
        )

    def set_native_raster(self, event: NativeMapEvent) -> None:
        """Set native whole-raster background image.

        Rust bridge is bundled; ValueError propagates to caller.
        """
        if self._data.background_image.set_native_raster(
            event.base64_map,
            event.width,
            event.height,
            event.x_min,
            event.y_max,
            event.resolution,
        ):
            self._on_change()

    def generate_svg(self) -> str | None:
        """Generate SVG image."""
        return self._data.generate_svg(
            [*self._map_subsets.values(), *self._native_map_subsets.values()],
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

    def reset_map_content(self) -> None:
        """Reset Rust backing so stale raster/map_info cannot survive selection."""
        self._data = MapDataRs()
        self._map_subsets.clear()
        self._native_map_subsets.clear()
        self._positions = []
        self._rotation = RotationAngle.DEG_0
        self._room_handling.clear()
        self._on_change()

    def teardown(self) -> None:
        """Teardown map data."""
        self._room_handling.teardown()
