"""Native room edit commands (Y1 Pro opcodes 50005, 50007, 50009)."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import orjson

from deebot_client.command import CommandMqttP2P, InitParam
from deebot_client.events.map import NativeMapRefreshEvent
from deebot_client.message import HandlingResult, HandlingState

from .common import JsonCommandMqttP2P
from .native_area import coord_to_cm
from .native_common import NativeExecuteCommand
from .native_map import GetNativeMapData

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deebot_client.event_bus import EventBus


def _validate_map_id(map_id: str) -> str:
    if not map_id or not map_id.strip() or map_id.strip() == "0":
        msg = "map_id must be a non-empty string"
        raise ValueError(msg)
    return map_id.strip()


def _validate_int_id(val: int, label: str) -> int:
    if isinstance(val, bool) or not isinstance(val, int):
        msg = f"{label} must be a non-boolean integer: {val}"
        raise TypeError(msg)
    return val


class NativeSplitRoom(NativeExecuteCommand, JsonCommandMqttP2P):
    """Split a room by cutting line (opcode 50005)."""

    NAME = "50005"
    _mqtt_params = MappingProxyType(
        {
            "mapId": InitParam(str, "map_id"),
            "roomId": InitParam(int, "room_id"),
            "points": InitParam(str, "points_raw"),
        }
    )

    def __init__(
        self,
        map_id: str,
        room_id: int,
        points: Sequence[int | float] | str,
        *,
        in_mm: bool = False,
    ) -> None:
        valid_map_id = _validate_map_id(map_id)
        valid_room_id = _validate_int_id(room_id, "Room ID")
        self.map_id = valid_map_id
        self.room_id = valid_room_id

        if isinstance(points, str):
            try:
                coords_cm = [int(float(c)) for c in points.split(",") if c.strip()]
            except ValueError as err:
                msg = f"Invalid points string: {points!r}"
                raise ValueError(msg) from err
        else:
            coords_cm = [coord_to_cm(c, in_mm=in_mm) for c in points]
        if len(coords_cm) != 4:
            msg = (
                "Split line requires exactly 4 coordinates [x1, y1, x2, y2], "
                f"got {len(coords_cm)}"
            )
            raise ValueError(msg)
        if coords_cm[0] == coords_cm[2] and coords_cm[1] == coords_cm[3]:
            msg = "Split cutting line cannot be degenerate (zero length)"
            raise ValueError(msg)

        points_str = ",".join(str(c) for c in coords_cm)
        super().__init__(
            {
                "mapId": valid_map_id,
                "roomId": valid_room_id,
                "points": points_str,
            }
        )

    @classmethod
    def create_from_mqtt(cls, payload: str | bytes | bytearray) -> CommandMqttP2P:
        """Reconstruct split command from MQTT request data."""
        raw = orjson.loads(payload)
        data = raw["body"]["data"]
        return cls(str(data["mapId"]), int(data["roomId"]), str(data["points"]))

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        result = super()._handle_response(event_bus, response)
        if (
            result.state == HandlingState.SUCCESS
            and event_bus.capabilities.map
            and event_bus.capabilities.map.edit is not None
        ):
            result.requested_commands.append(GetNativeMapData.get_map(self.map_id))
        return result

    def _handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        result = self.handle(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.notify(NativeMapRefreshEvent(self.map_id))


class NativeMergeRooms(NativeExecuteCommand, JsonCommandMqttP2P):
    """Merge two rooms into one (opcode 50007)."""

    NAME = "50007"
    _mqtt_params = MappingProxyType(
        {
            "mapId": InitParam(str, "map_id"),
            "roomIds": InitParam(list, "room_ids"),
        }
    )

    def __init__(
        self,
        map_id: str,
        room_ids: Sequence[int],
    ) -> None:
        valid_map_id = _validate_map_id(map_id)
        if len(room_ids) != 2:
            msg = f"Merge rooms requires exactly 2 room IDs, got {len(room_ids)}"
            raise ValueError(msg)

        r1 = _validate_int_id(room_ids[0], "Room ID 1")
        r2 = _validate_int_id(room_ids[1], "Room ID 2")
        if r1 == r2:
            msg = f"Merge room IDs must be distinct: {r1} == {r2}"
            raise ValueError(msg)

        self.map_id = valid_map_id
        self.room_ids = [r1, r2]
        super().__init__(
            {
                "mapId": valid_map_id,
                "roomIds": [r1, r2],
            }
        )

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        result = super()._handle_response(event_bus, response)
        if (
            result.state == HandlingState.SUCCESS
            and event_bus.capabilities.map
            and event_bus.capabilities.map.edit is not None
        ):
            result.requested_commands.append(GetNativeMapData.get_map(self.map_id))
        return result

    def _handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        result = self.handle(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.notify(NativeMapRefreshEvent(self.map_id))


class NativeRenameRoom(NativeExecuteCommand, JsonCommandMqttP2P):
    """Rename a room (opcode 50009)."""

    NAME = "50009"
    _mqtt_params = MappingProxyType(
        {
            "mapId": InitParam(str, "map_id"),
            "roomId": InitParam(int, "room_id"),
            "name": InitParam(str, "name"),
        }
    )

    def __init__(
        self,
        map_id: str,
        room_id: int,
        name: str,
    ) -> None:
        valid_map_id = _validate_map_id(map_id)
        valid_room_id = _validate_int_id(room_id, "Room ID")

        if not name or not name.strip():
            msg = "Room name must be a non-empty string"
            raise ValueError(msg)

        self.map_id = valid_map_id
        self.room_id = valid_room_id
        self.new_name = name.strip()
        # Map wire field to constructor name for generic MQTT reconstruction.
        self.name = self.new_name
        super().__init__(
            {
                "mapId": valid_map_id,
                "roomId": valid_room_id,
                "name": self.new_name,
            }
        )

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        result = super()._handle_response(event_bus, response)
        if (
            result.state == HandlingState.SUCCESS
            and event_bus.capabilities.map
            and event_bus.capabilities.map.edit is not None
        ):
            result.requested_commands.append(GetNativeMapData.get_map(self.map_id))
        return result

    def _handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        result = self.handle(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.notify(NativeMapRefreshEvent(self.map_id))


def native_split_room(
    map_id: str, room_id: int, points: Sequence[int | float]
) -> NativeSplitRoom:
    """Create NativeSplitRoom command with coordinates adapted from mm to cm."""
    return NativeSplitRoom(map_id, room_id, points, in_mm=True)


def native_merge_rooms(map_id: str, room_ids: Sequence[int]) -> NativeMergeRooms:
    """Create NativeMergeRooms command."""
    return NativeMergeRooms(map_id, room_ids)


def native_rename_room(map_id: str, room_id: int, name: str) -> NativeRenameRoom:
    """Create NativeRenameRoom command."""
    return NativeRenameRoom(map_id, room_id, name)
