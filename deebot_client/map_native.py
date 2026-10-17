"""Native map inspection coordination (Y1 Pro)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .commands.json.native_map import GetNativeMapData
from .events import (
    MapSetType,
    MapSubsetEvent,
    NativeMapEvent,
    NativeTraceEvent,
    Position,
    PositionsEvent,
)
from .logging_filter import get_logger
from .map_ids import valid_mid

if TYPE_CHECKING:
    from .device import DeviceCommandExecute
    from .events.map import Map as SavedMap
    from .map_data import MapData
    from .rs.map import RotationAngle

_LOGGER = get_logger(__name__)

__all__ = ["NativeMapCoordinator"]


class NativeMapCoordinator:
    """Track active vs inspected map plus pose/trace cursors."""

    def __init__(
        self,
        execute_command: DeviceCommandExecute,
        map_data: MapData,
    ) -> None:
        self._execute_command = execute_command
        self._map_data = map_data
        self.current_map_id: str | None = None
        self.active_map_id: str | None = None
        self.inspecting = False
        self.current_trace_id: int | None = None
        self.trace_map_id: str | None = None
        self.pose_by_type: dict[str, Position] = {}

    def select(self, map_id: str) -> bool:
        """Explicit inspection selection, True when display changed."""
        valid = valid_mid(map_id)
        if valid is None:
            msg = f"map_id must be a non-empty string: {map_id!r}"
            raise ValueError(msg)
        self.inspecting = True
        if self.current_map_id != valid:
            self.current_map_id = valid
            return True
        return False

    def catalog_angle(
        self, maps: set[SavedMap], map_id: str | None
    ) -> RotationAngle | None:
        """Return catalog rotation for a map id, if listed."""
        for saved in maps:
            if saved.id == map_id:
                return saved.angle
        return None

    def note_catalog(self, used_id: str | None) -> bool:
        """Record catalog active, follow when not inspecting."""
        self.active_map_id = used_id
        if self.current_map_id is None:
            self.current_map_id = used_id
            return False
        if not self.inspecting and self.current_map_id != used_id:
            self.current_map_id = used_id
            return True
        return False

    def clear_cursor(self) -> None:
        """Clear pose and trace cursors on map change."""
        self.pose_by_type.clear()
        self.current_trace_id = None
        self.trace_map_id = None

    def merge_positions(self, event: PositionsEvent) -> list[Position] | None:
        """Merge native deltas per type; legacy None means full replace."""
        if event.map_id is None:
            self.pose_by_type.clear()
            return list(event.positions)
        if valid_mid(event.map_id) is None:
            return None
        if self.current_map_id is not None and event.map_id != self.current_map_id:
            return None
        for pos in event.positions:
            self.pose_by_type[str(pos.type)] = pos
        return list(self.pose_by_type.values())

    def accept_raster(self, map_id: str) -> bool:
        """Decide raster acceptance; False drops stale/transient."""
        valid = valid_mid(map_id)
        if valid is None:
            return False
        if self.current_map_id is None:
            self.current_map_id = valid
            return True
        if valid == self.current_map_id:
            return True
        if self.inspecting:
            return False
        if self.active_map_id is not None and valid != self.active_map_id:
            return False
        self.current_map_id = valid
        return True

    def accept_trace(self, map_id: str) -> bool:
        """Decide trace acceptance without mutating cursors."""
        if valid_mid(map_id) is None:
            return False
        if self.current_map_id is not None and map_id != self.current_map_id:
            return False
        if self.current_map_id is None:
            self.current_map_id = map_id
        return True

    def note_trace(self, map_id: str, trace_id: int) -> None:
        """Record successful trace cursor."""
        self.current_trace_id = trace_id
        self.trace_map_id = map_id

    async def recover_full_trace(self, map_id: str) -> None:
        """Read-only full-trace recovery; prior valid trace preserved."""
        try:
            await self._execute_command(GetNativeMapData.get_traces(map_id))
        except Exception as err:
            _LOGGER.debug("Full trace recovery failed: %s", err)

    async def on_map(self, event: NativeMapEvent) -> None:
        """Apply a raster belonging to the displayed map."""
        previous = self.current_map_id
        if not self.accept_raster(event.map_id):
            return
        if previous != self.current_map_id:
            self._map_data.reset_map_content()
            self.clear_cursor()
        try:
            self._map_data.set_native_raster(event)
        except ValueError as err:
            _LOGGER.warning("Dropping native raster: %s", err)

    async def on_trace(self, event: NativeTraceEvent) -> None:
        """Apply a trace chunk without mixing streams."""
        if not self.accept_trace(event.map_id):
            return
        if not event.base64_trace:
            if event.start == 0:
                self._map_data.clear_trace_points()
                self.note_trace(event.map_id, event.trace_id)
            return
        if (
            self.current_trace_id is not None
            and event.trace_id != self.current_trace_id
            and event.start != 0
        ):
            await self.recover_full_trace(event.map_id)
            return
        try:
            self._map_data.set_native_trace(
                event.base64_trace, event.lz4_len, event.start, event.total_count
            )
        except ValueError as err:
            _LOGGER.warning("Trace chunk failed, recovering full trace: %s", err)
            await self.recover_full_trace(event.map_id)
            return
        self.note_trace(event.map_id, event.trace_id)

    def subset_key(self, event: MapSubsetEvent) -> tuple[MapSetType, int] | None:
        """Return store key or None to drop stale/transient/room subsets."""
        if event.type == MapSetType.ROOMS:
            return None
        if event.map_id is not None:
            if valid_mid(event.map_id) is None:
                return None
            if self.current_map_id is not None and event.map_id != self.current_map_id:
                return None
        return (event.type, event.id)

    def prune_keys(
        self,
        subsets: dict[tuple[MapSetType, int], MapSubsetEvent],
        type_: MapSetType,
        map_id: str,
        live: list[int],
    ) -> list[tuple[MapSetType, int]]:
        """Return stale subset keys for a MapSet prune."""
        if type_ == MapSetType.ROOMS or valid_mid(map_id) is None:
            return []
        if self.current_map_id is not None and map_id != self.current_map_id:
            return []
        return [
            key
            for key, sub in subsets.items()
            if sub.type == type_
            and (sub.map_id is None or sub.map_id == map_id)
            and key[1] not in live
        ]
