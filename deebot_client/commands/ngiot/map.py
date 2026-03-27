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
from deebot_client.rs.map import PositionType, RotationAngle

from .common import NgiotJsonGetCommand

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo
    from deebot_client.ngiot_client import NgiotClient


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


class GetCachedMapInfo(NgiotMapGetCommand):
    """Get cached map info for NGIOT devices."""

    NAME = "getCachedMapInfo"

    @property
    def _fields(self) -> Sequence[str]:
        return ("mapInfos",)

    @classmethod
    def _handle_body_data_dict(cls, event_bus: EventBus, data: dict[str, Any]) -> HandlingResult:
        return HandlingResult.analyse()

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
        map_data = data.get("mapData")
        if not isinstance(map_data, dict):
            return HandlingResult.analyse()

        map_blob = map_data.get("map")
        if not isinstance(map_blob, str) or not map_blob:
            return HandlingResult.analyse()

        map_id = str(data.get("mapId") or map_data.get("mapId") or "")
        crc = binascii.crc32(map_blob.encode("utf-8")) & 0xFFFFFFFF

        event_bus.notify(MajorMapEvent(map_id=map_id, values=[crc], requested=False))

        positions: list[Position] = []

        pos = data.get("pos")
        if isinstance(pos, dict):
            positions.append(
                Position(
                    type=PositionType.from_str("deebotPos"),
                    x=int(pos["x"]),
                    y=int(pos["y"]),
                    a=int(pos.get("a", 0)),
                )
            )

        deebot_pos = data.get("deebotPos")
        if isinstance(deebot_pos, dict):
            positions.append(
                Position(
                    type=PositionType.from_str("deebotPos"),
                    x=int(deebot_pos["x"]),
                    y=int(deebot_pos["y"]),
                    a=int(deebot_pos.get("a", 0)),
                )
            )

        charge_pos = map_data.get("chargePos")
        if isinstance(charge_pos, dict):
            positions.append(
                Position(
                    type=PositionType.from_str("chargePos"),
                    x=int(charge_pos["x"]),
                    y=int(charge_pos["y"]),
                    a=int(charge_pos.get("a", 0)),
                )
            )

        legacy_charge_pos = data.get("chargePos")
        if isinstance(legacy_charge_pos, list):
            for entry in legacy_charge_pos:
                if isinstance(entry, dict):
                    positions.append(
                        Position(
                            type=PositionType.from_str("chargePos"),
                            x=int(entry["x"]),
                            y=int(entry["y"]),
                            a=int(entry.get("a", 0)),
                        )
                    )

        if positions:
            event_bus.notify(PositionsEvent(positions=positions))

        return HandlingResult.success()


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
        # Instance-specific handling is done in _handle_response
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
        trace_data = data.get("mapTraceData")
        if not isinstance(trace_data, dict):
            return HandlingResult.analyse()

        trace = str(trace_data.get("trace", "")).strip()
        event_bus.notify(
            MapTraceEvent(
                start=int(trace_data.get("start", 0)),
                total=int(trace_data.get("totalCount", 0)),
                data=trace,
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
        positions: list[Position] = []

        pos = data.get("pos")
        if isinstance(pos, dict):
            positions.append(
                Position(
                    type=PositionType.from_str("deebotPos"),
                    x=int(pos["x"]),
                    y=int(pos["y"]),
                    a=int(pos.get("a", 0)),
                )
            )

        map_data = data.get("mapData")
        if isinstance(map_data, dict):
            charge_pos = map_data.get("chargePos")
            if isinstance(charge_pos, dict):
                positions.append(
                    Position(
                        type=PositionType.from_str("chargePos"),
                        x=int(charge_pos["x"]),
                        y=int(charge_pos["y"]),
                        a=int(charge_pos.get("a", 0)),
                    )
                )

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
        # Instance-specific handling is done in _handle_response
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

        map_id = str(data.get("mapId") or self._map_id)

        if self._map_type == MapSetType.ROOMS:
            areas = data.get("areas")
            if not isinstance(areas, list):
                return HandlingResult.analyse()

            rooms = [
                Room(
                    name=(str(area.get("name", "")).strip() or f"Area {int(area['id'])}"),
                    id=int(area["id"]),
                    coordinates="",
                )
                for area in areas
                if isinstance(area, dict) and area.get("id") is not None
            ]
            event_bus.notify(RoomsEvent(map_id=map_id, rooms=rooms))
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