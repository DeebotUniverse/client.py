"""NGIOT map commands."""

from __future__ import annotations

import binascii
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from deebot_client.events import Position, PositionsEvent, RoomsEvent
from deebot_client.events.map import (
    CachedMapInfoEvent,
    MajorMapEvent,
    Map,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
)
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import Room
from deebot_client.ngiot_client import APN_MAP_DETAILS
from deebot_client.ngiot_map_parser import (
    parse_areas,
    parse_base_map,
    parse_map_infos,
    parse_overlays,
    parse_pose,
    parse_trace,
    resolve_map_id,
)
from deebot_client.ngiot_map_state import NgiotMapStateStore
from deebot_client.rs.map import PositionType, RotationAngle

from .common import NgiotJsonGetCommand

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo
    from deebot_client.ngiot_client import NgiotClient


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _build_position(raw: Any, type_name: str) -> Position | None:
    if not isinstance(raw, dict):
        return None

    if raw.get("x") is None or raw.get("y") is None:
        return None

    return Position(
        type=PositionType.from_str(type_name),
        x=_coerce_int(raw.get("x")),
        y=_coerce_int(raw.get("y")),
        a=_coerce_int(raw.get("a")),
    )


def _build_position_from_point(raw_point: Any, type_name: str) -> Position | None:
    if raw_point is None:
        return None

    x = getattr(raw_point, "x", None)
    y = getattr(raw_point, "y", None)
    a = getattr(raw_point, "a", 0)

    if x is None or y is None:
        return None

    return Position(
        type=PositionType.from_str(type_name),
        x=_coerce_int(x),
        y=_coerce_int(y),
        a=_coerce_int(a),
    )


def _get_ngiot_map_state_store(event_bus: EventBus) -> NgiotMapStateStore:
    store = getattr(event_bus, "_ngiot_map_state_store", None)
    if store is None:
        store = NgiotMapStateStore()
        setattr(event_bus, "_ngiot_map_state_store", store)
    return store


def _resolve_effective_map_id(
    event_bus: EventBus,
    data: dict[str, Any],
    explicit: str = "",
) -> str:
    store = _get_ngiot_map_state_store(event_bus)
    return resolve_map_id(data, fallback=explicit or store.active_map_id or "")


def _polygon_to_coordinates(points: list[Any]) -> str:
    return ",".join(f"{point.x},{point.y}" for point in points)


class NgiotMapGetCommand(NgiotJsonGetCommand, ABC):
    """Base class for NGIOT APN 30001 field queries."""

    def __init__(self, map_id: str = "") -> None:
        super().__init__({})
        self._map_id = str(map_id)

    @property
    @abstractmethod
    def _fields(self) -> Sequence[str]:
        """Return fields to request from APN 30001."""

    async def _resolve_map_id(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> str:
        if self._map_id:
            return self._map_id

        response = await client.request(
            device_info,
            apn=APN_MAP_DETAILS,
            body_data={"fields": ["mapInfos"]},
        )
        data = response.get("body", {}).get("data", {})
        map_infos = data.get("mapInfos", [])
        if isinstance(map_infos, list):
            active = next(
                (
                    entry
                    for entry in map_infos
                    if isinstance(entry, dict) and int(entry.get("status", 0)) == 1
                ),
                None,
            )
            if isinstance(active, dict):
                return str(active.get("mapId", ""))

            fallback = next(
                (entry for entry in map_infos if isinstance(entry, dict)),
                None,
            )
            if isinstance(fallback, dict):
                return str(fallback.get("mapId", ""))

        return ""

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        body_data: dict[str, Any] = {"fields": list(self._fields)}
        map_id = await self._resolve_map_id(client, device_info)
        if map_id:
            body_data["mapId"] = map_id

        return await client.request(
            device_info,
            apn=APN_MAP_DETAILS,
            body_data=body_data,
        )

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        infos = parse_map_infos(data)
        if not infos:
            return HandlingResult.analyse()

        store = _get_ngiot_map_state_store(event_bus)
        store.update_map_infos(infos)

        maps = {
            Map(
                id=info.map_id,
                name=info.name,
                using=info.using,
                built=True,
                angle=RotationAngle.from_int(info.angle),
            )
            for info in infos
        }
        event_bus.notify(CachedMapInfoEvent(maps=maps))

        active_info = next((info for info in infos if info.using), None)
        resolved_info = active_info or infos[0]

        charger_pos = _build_position_from_point(
            resolved_info.charge_pos, "chargePos"
        )
        if charger_pos is not None:
            event_bus.notify(PositionsEvent(positions=[charger_pos]))

        return HandlingResult(
            HandlingState.SUCCESS,
            {"map_id": resolved_info.map_id},
        )

    def _handle_response(
        self,
        event_bus: EventBus,
        response: dict[str, Any],
    ) -> HandlingResult:
        result = super()._handle_response(event_bus, response)
        if (
            result.state == HandlingState.SUCCESS
            and result.args
            and (map_obj := event_bus.capabilities.map)
        ):
            map_id = result.args["map_id"]
            result.requested_commands.extend(
                [map_obj.set.execute(map_id, entry) for entry in MapSetType]
            )
            if map_obj.info:
                result.requested_commands.append(map_obj.info.execute(map_id))
        return result


class GetMajorMap(NgiotMapGetCommand):
    """Get the current NGIOT raster map."""

    NAME = "getMajorMap"

    @property
    def _fields(self) -> Sequence[str]:
        return ("mapData", "areas", "pos")

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus: EventBus,
        data: dict[str, Any],
    ) -> HandlingResult:
        store = _get_ngiot_map_state_store(event_bus)
        map_id = _resolve_effective_map_id(event_bus, data)
        handled = False

        map_data = data.get("mapData")
        if isinstance(map_data, dict):
            legacy_map_blob = map_data.get("map")
            if isinstance(legacy_map_blob, str) and legacy_map_blob:
                crc = binascii.crc32(legacy_map_blob.encode("utf-8")) & 0xFFFFFFFF
                event_bus.notify(
                    MajorMapEvent(map_id=map_id, values=[crc], requested=False)
                )
                handled = True

        base_map = parse_base_map(data, map_id)
        if base_map is not None and base_map.map_id:
            store.update_base_map(base_map)
            map_id = base_map.map_id
            handled = True

        areas = parse_areas(data)
        if areas and map_id:
            store.update_areas(map_id, areas)
            handled = True

        positions: list[Position] = []

        pose = parse_pose(data)
        if pose is not None:
            if map_id:
                store.update_pose(map_id, pose)
            positions.append(
                Position(
                    type=PositionType.from_str("deebotPos"),
                    x=pose.x,
                    y=pose.y,
                    a=pose.a,
                )
            )
            handled = True

        if isinstance(map_data, dict):
            charger_pos = _build_position(map_data.get("chargePos"), "chargePos")
            if charger_pos is not None:
                positions.append(charger_pos)
                handled = True

        legacy_charge_pos = data.get("chargePos")
        if isinstance(legacy_charge_pos, list):
            for entry in legacy_charge_pos:
                charger_pos = _build_position(entry, "chargePos")
                if charger_pos is not None:
                    positions.append(charger_pos)
                    handled = True

        if positions:
            event_bus.notify(PositionsEvent(positions=positions))

        return HandlingResult.success() if handled else HandlingResult.analyse()


class GetCachedMapInfo(NgiotMapGetCommand):
    NAME = "getCachedMapInfo"

    @property
    def _fields(self) -> Sequence[str]:
        return ("mapInfos",)


class GetMinorMap(NgiotMapGetCommand):
    """Compatibility command for NGIOT map tile fetches."""

    NAME = "getMinorMap"

    def __init__(self, piece_index: int, map_id: str) -> None:
        super().__init__(map_id)
        self._piece_index = piece_index

    @property
    def _fields(self) -> Sequence[str]:
        return ("mapData",)

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus: EventBus,
        data: dict[str, Any],
    ) -> HandlingResult:
        del event_bus, data
        return HandlingResult.analyse()

    def _handle_response(
        self,
        event_bus: EventBus,
        response: dict[str, Any],
    ) -> HandlingResult:
        if response.get("ret") != "ok":
            return HandlingResult.analyse()

        body = response.get("resp", {}).get("body", {})
        data = body.get("data", {})
        if not isinstance(data, dict):
            return HandlingResult.analyse()

        map_data = data.get("mapData")
        if not isinstance(map_data, dict):
            return HandlingResult.analyse()

        map_blob = map_data.get("map")
        if not isinstance(map_blob, str) or not map_blob:
            return HandlingResult.analyse()

        event_bus.notify(MinorMapEvent(index=self._piece_index, value=map_blob))
        return HandlingResult.success()


class GetMapTrace(NgiotMapGetCommand):
    """Get the current NGIOT map trace."""

    NAME = "getMapTrace"

    @property
    def _fields(self) -> Sequence[str]:
        return ("mapTraceData",)

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus: EventBus,
        data: dict[str, Any],
    ) -> HandlingResult:
        trace = parse_trace(data)
        if trace is None:
            return HandlingResult.analyse()

        store = _get_ngiot_map_state_store(event_bus)
        map_id = _resolve_effective_map_id(event_bus, data)
        if map_id:
            store.update_trace(map_id, trace)

        event_bus.notify(
            MapTraceEvent(
                start=trace.start,
                total=trace.total_count,
                data=trace.encoded,
                lz4_len=trace.lz4_len,
            )
        )
        return HandlingResult.success()


class GetPos(NgiotMapGetCommand):
    """Get current robot and charger positions from NGIOT map data."""

    NAME = "getPos"

    @property
    def _fields(self) -> Sequence[str]:
        return ("mapData", "pos")

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus: EventBus,
        data: dict[str, Any],
    ) -> HandlingResult:
        store = _get_ngiot_map_state_store(event_bus)
        map_id = _resolve_effective_map_id(event_bus, data)

        positions: list[Position] = []

        pose = parse_pose(data)
        if pose is not None:
            if map_id:
                store.update_pose(map_id, pose)

            positions.append(
                Position(
                    type=PositionType.from_str("deebotPos"),
                    x=pose.x,
                    y=pose.y,
                    a=pose.a,
                )
            )

        map_data = data.get("mapData")
        if isinstance(map_data, dict):
            charger_pos = _build_position(map_data.get("chargePos"), "chargePos")
            if charger_pos is not None:
                positions.append(charger_pos)

        legacy_charge_pos = data.get("chargePos")
        if isinstance(legacy_charge_pos, list):
            for entry in legacy_charge_pos:
                charger_pos = _build_position(entry, "chargePos")
                if charger_pos is not None:
                    positions.append(charger_pos)

        if positions:
            event_bus.notify(PositionsEvent(positions=positions))
            return HandlingResult.success()

        return HandlingResult.analyse()


class GetMapSet(NgiotMapGetCommand):
    """Get room and barrier data from the NGIOT map surface."""

    NAME = "getMapSubSet"

    def __init__(
        self,
        mid: str,
        type: MapSetType | str = MapSetType.ROOMS,
    ) -> None:
        if isinstance(type, MapSetType):
            type = type.value

        super().__init__(mid)
        self._map_type = MapSetType(type)

    @property
    def _fields(self) -> Sequence[str]:
        if self._map_type == MapSetType.ROOMS:
            return ("areas",)
        return ("virtualWalls", "mopWalls", "carpets")

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus: EventBus,
        data: dict[str, Any],
    ) -> HandlingResult:
        del event_bus, data
        return HandlingResult.analyse()

    def _handle_response(
        self,
        event_bus: EventBus,
        response: dict[str, Any],
    ) -> HandlingResult:
        if response.get("ret") != "ok":
            return HandlingResult.analyse()

        body = response.get("resp", {}).get("body", {})
        data = body.get("data", {})
        if not isinstance(data, dict):
            return HandlingResult.analyse()

        store = _get_ngiot_map_state_store(event_bus)
        map_id = _resolve_effective_map_id(event_bus, data, self._map_id)

        if self._map_type == MapSetType.ROOMS:
            areas = parse_areas(data)
            if not areas:
                return HandlingResult.analyse()

            if map_id:
                store.update_areas(map_id, areas)

            rooms = [
                Room(
                    name=(area.name or f"Area {_coerce_int(area.area_id, index)}"),
                    id=_coerce_int(area.area_id, index),
                    coordinates=_polygon_to_coordinates(area.polygon),
                )
                for index, area in enumerate(areas)
            ]
            event_bus.notify(RoomsEvent(map_id=map_id, rooms=rooms))
            return HandlingResult.success()

        overlays = parse_overlays(data)
        if map_id and overlays:
            store.update_overlays(map_id, overlays)

        overlay_type_map = {
            MapSetType.VIRTUAL_WALLS: "virtual_walls",
            MapSetType.NO_MOP_ZONES: "mop_walls",
        }
        target_overlay_type = overlay_type_map.get(self._map_type)

        if target_overlay_type:
            parsed_for_type = [
                overlay
                for overlay in overlays
                if overlay.overlay_type == target_overlay_type
            ]

            if parsed_for_type:
                subset_ids: list[int] = []
                for index, overlay in enumerate(parsed_for_type):
                    subset_id = _coerce_int(overlay.overlay_id, index)
                    subset_ids.append(subset_id)
                    event_bus.notify(
                        MapSubsetEvent(
                            id=subset_id,
                            type=self._map_type,
                            coordinates=_polygon_to_coordinates(overlay.polygon),
                        )
                    )

                event_bus.notify(MapSetEvent(self._map_type, subset_ids, map_id))
                return HandlingResult.success()

        data_key = {
            MapSetType.VIRTUAL_WALLS: "virtualWalls",
            MapSetType.NO_MOP_ZONES: "mopWalls",
        }[self._map_type]
        raw_value = str(data.get(data_key, "")).strip()
        subset_ids: list[int] = []

        if raw_value:
            for entry in raw_value.split(";"):
                parts = [part.strip() for part in entry.split(",") if part.strip()]
                if len(parts) < 3:
                    continue

                subset_id = int(parts[0])
                coordinates = ",".join(parts[2:] if len(parts) % 2 == 0 else parts[1:])
                subset_ids.append(subset_id)
                event_bus.notify(
                    MapSubsetEvent(
                        id=subset_id,
                        type=self._map_type,
                        coordinates=coordinates,
                    )
                )

        event_bus.notify(MapSetEvent(self._map_type, subset_ids, map_id))
        return HandlingResult.success()


# Backward compatibility for older imports
GetMapSubSet = GetMapSet