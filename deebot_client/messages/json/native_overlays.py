"""Native wall overlay parsing (Y1 Pro virtual/mop walls)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import MapSetEvent, MapSetType, MapSubsetEvent
from deebot_client.logging_filter import get_logger

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


def _wall_entries(raw_walls: str) -> list[list[str]]:
    entries: list[list[str]] = []
    if raw_walls.strip():
        for entry in raw_walls.split(";"):
            parts = [p.strip() for p in entry.split(",") if p.strip()]
            if parts:
                entries.append(parts)
    return entries


def _parse_virtual_walls(event_bus: EventBus, map_id: str, raw_walls: str) -> None:
    wall_ids: list[int] = []
    for parts in _wall_entries(raw_walls):
        if len(parts) >= 6:
            try:
                wid = int(parts[0])
                coords = [int(float(c)) * 10 for c in parts[2:6]]
            except ValueError, TypeError:
                _LOGGER.debug("Skipping malformed virtual wall entry")
                continue
            event_bus.notify(
                MapSubsetEvent(
                    id=wid,
                    type=MapSetType.VIRTUAL_WALLS,
                    coordinates=",".join(str(c) for c in coords),
                    map_id=map_id,
                )
            )
            wall_ids.append(wid)
    event_bus.notify(
        MapSetEvent(
            type=MapSetType.VIRTUAL_WALLS,
            subsets=wall_ids,
            map_id=map_id,
        )
    )


def _parse_mop_walls(event_bus: EventBus, map_id: str, raw_walls: str) -> None:
    zone_ids: list[int] = []
    for parts in _wall_entries(raw_walls):
        if len(parts) >= 8:
            try:
                zid = int(parts[0])
                coords = [int(float(c)) * 10 for c in parts[2:]]
            except ValueError, TypeError:
                _LOGGER.debug("Skipping malformed mop zone entry")
                continue
            event_bus.notify(
                MapSubsetEvent(
                    id=zid,
                    type=MapSetType.NO_MOP_ZONES,
                    coordinates=",".join(str(c) for c in coords),
                    map_id=map_id,
                )
            )
            zone_ids.append(zid)
    event_bus.notify(
        MapSetEvent(
            type=MapSetType.NO_MOP_ZONES,
            subsets=zone_ids,
            map_id=map_id,
        )
    )


def emit_overlays(event_bus: EventBus, data: dict[str, Any], map_id: str) -> None:
    """Notify wall overlays for the display map id."""
    if "virtualWalls" in data:
        raw_walls = data["virtualWalls"]
        if not isinstance(raw_walls, str):
            _LOGGER.debug("Ignoring non-string virtualWalls")
        elif map_id:
            _parse_virtual_walls(event_bus, map_id, raw_walls)
    if "mopWalls" in data:
        raw_zones = data["mopWalls"]
        if not isinstance(raw_zones, str):
            _LOGGER.debug("Ignoring non-string mopWalls")
        elif map_id:
            _parse_mop_walls(event_bus, map_id, raw_zones)
