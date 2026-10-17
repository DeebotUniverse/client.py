"""Native numeric map edit commands (Y1 Pro cqyi87).

Opcodes:
- 50001: Virtual walls and no-mop zones (add/del)
- 50005: Split room by cutting line (see native_room_edit.py)
- 50007: Merge two rooms (see native_room_edit.py)
- 50009: Rename room (see native_room_edit.py)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import orjson

from deebot_client.capabilities import CapabilityMapEdit
from deebot_client.events import MapSetType
from deebot_client.events.map import NativeMapRefreshEvent
from deebot_client.message import HandlingResult, HandlingState

from .common import JsonCommandMqttP2P
from .native_area import build_add_overlay_args
from .native_common import NativeExecuteCommand
from .native_map import GetNativeMapData
from .native_room_edit import (
    NativeMergeRooms,
    NativeRenameRoom,
    NativeSplitRoom,
    _validate_int_id,
    _validate_map_id,
    native_merge_rooms,
    native_rename_room,
    native_split_room,
)

if TYPE_CHECKING:
    from deebot_client.command import CommandMqttP2P
    from deebot_client.event_bus import EventBus

__all__ = [
    "NativeAddNoMopZone",
    "NativeAddVirtualWall",
    "NativeDeleteNoMopZone",
    "NativeDeleteVirtualWall",
    "NativeMapOverlay",
    "NativeMergeRooms",
    "NativeRenameRoom",
    "NativeSplitRoom",
    "create_native_map_edit",
    "native_add_no_mop_zone",
    "native_add_virtual_wall",
    "native_delete_no_mop_zone",
    "native_delete_virtual_wall",
    "native_map_overlay",
    "native_merge_rooms",
    "native_rename_room",
    "native_split_room",
]


class NativeMapOverlay(NativeExecuteCommand, JsonCommandMqttP2P):
    """Native command for virtual walls and no-mop zones (opcode 50001)."""

    NAME = "50001"

    def __init__(
        self,
        action: str,
        kind: MapSetType,
        map_id: str,
        target: int | Sequence[int | float],
        *,
        in_mm: bool = False,
    ) -> None:
        valid_map_id = _validate_map_id(map_id)
        self.map_id = valid_map_id
        if action not in ("add", "del"):
            msg = f"Unsupported action: {action}. Must be 'add' or 'del'."
            raise ValueError(msg)

        if kind == MapSetType.VIRTUAL_WALLS:
            mode, _type_val = 1, 1
        elif kind == MapSetType.NO_MOP_ZONES:
            mode, _type_val = 2, 2
        else:
            msg = f"Unsupported kind for map overlay: {kind}"
            raise ValueError(msg)

        if action == "add":
            if not isinstance(target, Sequence) or isinstance(target, (str, bytes)):
                msg = f"Coordinates sequence required when adding overlay, got: {type(target)}"
                raise TypeError(msg)
            args = build_add_overlay_args(kind, valid_map_id, target, in_mm=in_mm)
        else:
            if isinstance(target, bool) or not isinstance(target, int):
                msg = f"Overlay ID must be a non-boolean integer: {target}"
                raise TypeError(msg)
            valid_id = _validate_int_id(target, "Overlay ID")
            args = {
                "action": "del",
                "mode": mode,
                "mapId": valid_map_id,
                "id": valid_id,
            }

        super().__init__(args)

    @classmethod
    def create_from_mqtt(cls, payload: str | bytes | bytearray) -> CommandMqttP2P:
        """Reconstruct overlay command from MQTT request data."""
        raw = orjson.loads(payload)
        data = raw["body"]["data"]
        action = str(data["action"])
        mode = int(data["mode"])
        kind = MapSetType.VIRTUAL_WALLS if mode == 1 else MapSetType.NO_MOP_ZONES
        map_id = str(data["mapId"])
        if action == "add":
            point = str(data["point"])
            coords = [int(float(c)) for c in point.split(",") if c.strip()]
            return cls(action, kind, map_id, coords)
        target = int(data["id"])
        return cls(action, kind, map_id, target)

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        result = super()._handle_response(event_bus, response)
        if (
            result.state == HandlingState.SUCCESS
            and event_bus.capabilities.map
            and event_bus.capabilities.map.edit is not None
        ):
            result.requested_commands.extend(
                [
                    GetNativeMapData.get_overlays(self.map_id),
                    GetNativeMapData.get_map(self.map_id),
                ]
            )
        return result

    def _handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        result = self.handle(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.notify(NativeMapRefreshEvent(self.map_id))


class NativeAddVirtualWall(NativeMapOverlay):
    """Add a virtual wall line."""

    def __init__(
        self,
        map_id: str,
        coordinates: Sequence[int | float],
        *,
        in_mm: bool = False,
    ) -> None:
        super().__init__(
            "add",
            MapSetType.VIRTUAL_WALLS,
            map_id,
            coordinates,
            in_mm=in_mm,
        )


class NativeDeleteVirtualWall(NativeMapOverlay):
    """Delete a virtual wall line."""

    def __init__(self, map_id: str, wall_id: int) -> None:
        super().__init__(
            "del",
            MapSetType.VIRTUAL_WALLS,
            map_id,
            wall_id,
        )


class NativeAddNoMopZone(NativeMapOverlay):
    """Add a restricted no-mop zone polygon."""

    def __init__(
        self,
        map_id: str,
        coordinates: Sequence[int | float],
        *,
        in_mm: bool = False,
    ) -> None:
        super().__init__(
            "add",
            MapSetType.NO_MOP_ZONES,
            map_id,
            coordinates,
            in_mm=in_mm,
        )


class NativeDeleteNoMopZone(NativeMapOverlay):
    """Delete a restricted no-mop zone."""

    def __init__(self, map_id: str, zone_id: int) -> None:
        super().__init__(
            "del",
            MapSetType.NO_MOP_ZONES,
            map_id,
            zone_id,
        )


def native_map_overlay(
    action: str,
    kind: MapSetType,
    map_id: str,
    target: int | Sequence[int | float],
) -> NativeMapOverlay:
    """Create NativeMapOverlay command with coordinates adapted from mm to cm."""
    return NativeMapOverlay(action, kind, map_id, target, in_mm=True)


def native_add_virtual_wall(
    map_id: str, coordinates: Sequence[int | float]
) -> NativeAddVirtualWall:
    """Create NativeAddVirtualWall command with coordinates adapted from mm to cm."""
    return NativeAddVirtualWall(map_id, coordinates, in_mm=True)


def native_delete_virtual_wall(map_id: str, wall_id: int) -> NativeDeleteVirtualWall:
    """Create NativeDeleteVirtualWall command."""
    return NativeDeleteVirtualWall(map_id, wall_id)


def native_add_no_mop_zone(
    map_id: str, coordinates: Sequence[int | float]
) -> NativeAddNoMopZone:
    """Create NativeAddNoMopZone command with coordinates adapted from mm to cm."""
    return NativeAddNoMopZone(map_id, coordinates, in_mm=True)


def native_delete_no_mop_zone(map_id: str, zone_id: int) -> NativeDeleteNoMopZone:
    """Create NativeDeleteNoMopZone command."""
    return NativeDeleteNoMopZone(map_id, zone_id)


def create_native_map_edit() -> CapabilityMapEdit:
    """Create native map edit capability bundle with mm-adapted-cm API."""
    return CapabilityMapEdit(
        add_virtual_wall=native_add_virtual_wall,
        delete_virtual_wall=native_delete_virtual_wall,
        add_no_mop_zone=native_add_no_mop_zone,
        delete_no_mop_zone=native_delete_no_mop_zone,
        split_room=native_split_room,
        merge_rooms=native_merge_rooms,
        rename_room=native_rename_room,
    )
