"""Native map and telemetry push parsing (Y1 Pro opcodes 30000 and 30001)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import (
    CachedMapInfoEvent,
    NativeMapEvent,
    NativeTraceEvent,
    Position,
    PositionsEvent,
    RoomsEvent,
)
from deebot_client.events.map import Map
from deebot_client.logging_filter import get_logger
from deebot_client.map_ids import valid_mid
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict
from deebot_client.models import Room
from deebot_client.rs.map import PositionType, RotationAngle

from .native_overlays import emit_overlays

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


def _parse_position_block(block: Any, kind: PositionType) -> Position | None:
    if not isinstance(block, dict):
        return None
    try:
        return Position(
            type=kind,
            x=int(block["x"]) * 10,
            y=int(block["y"]) * 10,
            a=int(block.get("a", 0)),
        )
    except KeyError, ValueError, TypeError:
        _LOGGER.debug("Skipping malformed position block")
        return None


def _emit_catalog(event_bus: EventBus, raw_infos: Any) -> str | None:
    """Notify map catalog; return active map id when present."""
    if not isinstance(raw_infos, list):
        _LOGGER.debug("Ignoring non-list mapInfos")
        return None
    active_map_id: str | None = None
    maps: set[Map] = set()
    for item in raw_infos:
        if not isinstance(item, dict):
            continue
        mid = valid_mid(item.get("mapId"))
        if mid is None:
            continue
        try:
            angle = RotationAngle.from_int(int(item.get("angle", 0)))
        except ValueError, TypeError:
            _LOGGER.debug("Skipping mapInfo with bad angle")
            continue
        is_using = item.get("status") == 1
        if is_using:
            active_map_id = mid
        maps.add(
            Map(
                id=mid,
                name=str(item.get("name") or ""),
                using=is_using,
                built=item.get("saved") == 1,
                angle=angle,
            )
        )
    event_bus.notify(CachedMapInfoEvent(maps=maps))
    return active_map_id


def _emit_raster(
    event_bus: EventBus, raw_map: Any, map_id: str
) -> tuple[str | None, Position | None]:
    """Notify raster event; return nested map id and dock position."""
    if not isinstance(raw_map, dict):
        _LOGGER.debug("Ignoring non-dict mapData")
        return None, None
    nested = valid_mid(raw_map.get("mapId"))
    effective = nested or map_id
    payload = raw_map.get("map")
    if isinstance(payload, str) and payload and effective:
        try:
            event_bus.notify(
                NativeMapEvent(
                    map_id=effective,
                    width=int(raw_map["width"]),
                    height=int(raw_map["height"]),
                    x_min=int(float(raw_map["xMin"])),
                    y_max=int(float(raw_map["yMax"])),
                    resolution=int(raw_map.get("resolution", 5)),
                    base64_map=payload,
                )
            )
        except (KeyError, ValueError, TypeError) as err:
            _LOGGER.warning("Could not parse native mapData raster: %s", err)
    elif payload:
        _LOGGER.debug("Skipping raster without usable map id")
    charge_block = raw_map.get("chargePos")
    charger = (
        _parse_position_block(charge_block, PositionType.CHARGER)
        if isinstance(charge_block, dict)
        else None
    )
    return nested, charger


def _emit_trace(event_bus: EventBus, raw_trace: Any, map_id: str) -> None:
    """Notify trace event for its nested or outer map id."""
    if not isinstance(raw_trace, dict):
        _LOGGER.debug("Ignoring non-dict mapTraceData")
        return
    trace_map_id = valid_mid(raw_trace.get("mapId")) or map_id
    if not trace_map_id:
        _LOGGER.debug("Skipping trace without usable map id")
        return
    try:
        raw_payload = raw_trace.get("trace")
        event_bus.notify(
            NativeTraceEvent(
                map_id=trace_map_id,
                trace_id=int(raw_trace.get("traceId", 0)),
                start=int(raw_trace.get("start", 0)),
                total_count=int(raw_trace.get("totalCount", 0)),
                lz4_len=int(raw_trace.get("lz4Len", 0)),
                base64_trace=str(raw_payload) if isinstance(raw_payload, str) else None,
            )
        )
    except (ValueError, TypeError) as err:
        _LOGGER.warning("Could not parse mapTraceData: %s", err)


def _emit_areas(event_bus: EventBus, raw_areas: Any, map_id: str) -> None:
    """Notify room catalog for the display map id."""
    if not isinstance(raw_areas, list):
        _LOGGER.debug("Ignoring non-list areas")
        return
    if not map_id:
        return
    rooms: list[Room] = []
    for area in raw_areas:
        if not isinstance(area, dict):
            continue
        try:
            room_id = int(area["id"])
            rooms.append(
                Room(
                    name=str(area.get("name") or f"Room {room_id}"),
                    id=room_id,
                    coordinates=(
                        f"{int(float(area.get('centerX', 0))) * 10},"
                        f"{int(float(area.get('centerY', 0))) * 10}"
                    ),
                )
            )
        except KeyError, ValueError, TypeError:
            _LOGGER.debug("Skipping malformed area entry")
            continue
    event_bus.notify(RoomsEvent(map_id=map_id, rooms=rooms))


def parse_native_map_data(
    event_bus: EventBus,
    data: dict[str, Any],
    fallback_map_id: str | None = None,
) -> HandlingResult:
    """Parse native map telemetry from opcode 30000 push or 30001 response.

    fallback_map_id carries requesting GetNativeMapData.map_id for replies
    with missing outer id. Transient ids 0/empty never become global alias.
    """
    if not isinstance(data, dict) or not data:
        return HandlingResult.success()

    active_map_id: str | None = None
    if "mapInfos" in data:
        active_map_id = _emit_catalog(event_bus, data["mapInfos"])

    outer = valid_mid(data.get("mapId"))
    requested = valid_mid(fallback_map_id)
    base = outer or requested or active_map_id or ""

    raster_nested: str | None = None
    charger: Position | None = None
    if "mapData" in data:
        raster_nested, charger = _emit_raster(event_bus, data["mapData"], base)

    display = base or raster_nested or ""
    if charger is not None and raster_nested is not None and raster_nested != display:
        charger = None
    positions: list[Position] = []
    pos_block = data.get("pos")
    robot = (
        _parse_position_block(pos_block, PositionType.DEEBOT)
        if isinstance(pos_block, dict)
        else None
    )
    if robot is not None:
        positions.append(robot)
    if charger is not None:
        positions.append(charger)
    if positions and display:
        event_bus.notify(PositionsEvent(positions=positions, map_id=display))

    if "mapTraceData" in data:
        _emit_trace(event_bus, data["mapTraceData"], base)

    if "areas" in data:
        _emit_areas(event_bus, data["areas"], display)

    emit_overlays(event_bus, data, display)

    if active_map_id:
        return HandlingResult(HandlingState.SUCCESS, args={"map_id": active_map_id})

    return HandlingResult.success()


class OnNativeMapReport(MessageBodyDataDict):
    """On native map telemetry report push message (opcode 30000)."""

    NAME = "30000"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        return parse_native_map_data(event_bus, data)
