"""Map module."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Final

from deebot_client.events.map import CachedMapInfoEvent, MapChangedEvent

from .commands.json.native_map import GetNativeMapData
from .events import (
    MajorMapEvent,
    MapInfoEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
    NativeMapEvent,
    NativeTraceEvent,
    PositionsEvent,
)
from .events.map import NativeMapRefreshEvent
from .exceptions import MapError
from .logging_filter import get_logger
from .map_data import MapData
from .map_ids import valid_mid
from .map_native import NativeMapCoordinator
from .util import cancel, create_task

if TYPE_CHECKING:
    from collections.abc import Callable

    from .capabilities import CapabilityMap
    from .device import DeviceCommandExecute
    from .event_bus import EventBus

_LOGGER = get_logger(__name__)

__all__ = ["Map", "MapData"]


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
        self._native_enabled = capabilities.trace.event is NativeTraceEvent
        self._map_data: Final[MapData] = MapData(event_bus)
        self._native: Final[NativeMapCoordinator] = NativeMapCoordinator(
            execute_command, self._map_data
        )
        self._last_image: str | None = None
        self._tasks: set[asyncio.Future[Any]] = set()
        self._unsubscribers: list[Callable[[], None]] = []

        async def on_map_set(event: MapSetEvent) -> None:
            if self._native_enabled:
                for key in self._native.prune_keys(
                    self._map_data.native_map_subsets,
                    event.type,
                    event.map_id,
                    event.subsets,
                ):
                    self._map_data.native_map_subsets.pop(key, None)
            elif event.type != MapSetType.ROOMS:
                for subset_id, subset in self._map_data.map_subsets.copy().items():
                    if subset.type == event.type and subset_id not in event.subsets:
                        self._map_data.map_subsets.pop(subset_id, None)

        self._unsubscribers.append(event_bus.subscribe(MapSetEvent, on_map_set))

        async def on_map_subset(event: MapSubsetEvent) -> None:
            if self._native_enabled:
                key = self._native.subset_key(event)
                if (
                    key is not None
                    and self._map_data.native_map_subsets.get(key) != event
                ):
                    self._map_data.native_map_subsets[key] = event
            elif (
                event.type != MapSetType.ROOMS
                and self._map_data.map_subsets.get(event.id) != event
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
        if self._native_enabled:
            self._unsubscribers.append(
                event_bus.subscribe(NativeMapRefreshEvent, self._on_native_refresh)
            )

    async def _subscribe_minor_major_map_events(self) -> list[Callable[[], None]]:
        if (minor := self._capabilities.minor) is None:
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

    async def _on_cached_info(self, event: CachedMapInfoEvent) -> None:
        if not self._native_enabled:
            used_map = next((m for m in event.maps if m.using), None)
            if used_map:
                self._map_data.set_rotation_angle(used_map.angle)
            return
        if not event.maps:
            self._native.active_map_id = None
            if not self._native.inspecting:
                self._native.current_map_id = None
                self._reset_map_content()
            return
        used_map = next((m for m in event.maps if m.using), None)
        if used_map and self._native.note_catalog(used_map.id):
            self._reset_map_content()
        angle = self._native.catalog_angle(event.maps, self.current_map_id)
        if angle is not None:
            self._map_data.set_rotation_angle(angle)

    async def _on_position(self, event: PositionsEvent) -> None:
        merged = self._native.merge_positions(event)
        if merged is not None:
            self._map_data.update_positions(merged)

    async def _on_map_trace(self, event: MapTraceEvent) -> None:
        if event.start == 0:
            self._map_data.clear_trace_points()
        if data := event.data.strip():
            self._map_data.add_trace_points(data)

    async def _on_native_refresh(self, event: NativeMapRefreshEvent) -> None:
        if (map_id := valid_mid(event.map_id)) is not None:
            await self._refresh_selected(map_id)

    async def _on_first_map_changed_subscription(self) -> Callable[[], None]:
        unsubscribers = await self._subscribe_minor_major_map_events()

        cached_map_subscribers = self._event_bus.has_subscribers(CachedMapInfoEvent)
        unsubscribers.append(
            self._event_bus.subscribe(CachedMapInfoEvent, self._on_cached_info)
        )
        if cached_map_subscribers:
            self._event_bus.request_refresh(CachedMapInfoEvent)

        unsubscribers.append(
            self._event_bus.subscribe(PositionsEvent, self._on_position)
        )
        unsubscribers.append(
            self._event_bus.subscribe(MapTraceEvent, self._on_map_trace)
        )
        if self._native_enabled:
            unsubscribers.append(
                self._event_bus.subscribe(NativeMapEvent, self._native.on_map)
            )
            unsubscribers.append(
                self._event_bus.subscribe(NativeTraceEvent, self._native.on_trace)
            )

        def unsub() -> None:
            for unsub in unsubscribers:
                unsub()

        return unsub

    @property
    def current_map_id(self) -> str | None:
        """Return currently loaded or selected map ID."""
        return self._native.current_map_id

    @property
    def active_map_id(self) -> str | None:
        """Return catalog active map ID."""
        return self._native.active_map_id

    def select_map(self, map_id: str) -> None:
        """Select map ID for inspection without device switch."""
        if self._native.select(map_id):
            self._reset_map_content()
        if self._native_enabled:
            cached = self._event_bus.get_last_event(CachedMapInfoEvent)
            if cached is not None:
                angle = self._native.catalog_angle(
                    cached.maps, self._native.current_map_id
                )
                if angle is not None:
                    self._map_data.set_rotation_angle(angle)

    async def fetch_map(self, map_id: str) -> None:
        """Inspect map and fetch raster, traces, and overlays (read-only)."""
        valid = valid_mid(map_id)
        if valid is None:
            msg = f"map_id must be a non-empty string: {map_id!r}"
            raise ValueError(msg)
        self.select_map(valid)
        await self._refresh_selected(valid)

    def _reset_map_content(self) -> None:
        self._map_data.reset_map_content()
        self._native.clear_cursor()
        self._last_image = None

    def refresh(self) -> None:
        """Manually refresh map."""
        if not self._unsubscribers:
            raise MapError("Please enable the map first")

        current = self._native.current_map_id
        if self._native_enabled and current is not None:
            create_task(self._tasks, self._refresh_selected(current))
            return

        self._event_bus.request_refresh(CachedMapInfoEvent)
        self._event_bus.request_refresh(PositionsEvent)
        self._event_bus.request_refresh(MapTraceEvent)
        if self._capabilities.major is not None:
            self._event_bus.request_refresh(MajorMapEvent)

    async def _refresh_selected(self, map_id: str) -> None:
        """Fetch raster, traces, and overlays for the captured map id."""
        async with asyncio.TaskGroup() as tg:
            for cmd in (
                GetNativeMapData.get_map(map_id),
                GetNativeMapData.get_traces(map_id),
                GetNativeMapData.get_overlays(map_id),
            ):
                tg.create_task(self._execute_command(cmd))

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
        await cancel(self._tasks)
        self._map_data.teardown()
