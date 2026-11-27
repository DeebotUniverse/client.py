"""Native numeric area and zone cleaning commands (Y1 Pro cqyi87).

Room cleaning (40007) and Zone cleaning (40005).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from deebot_client.events import MapSetType
from deebot_client.models import CleanMode

from .native_common import NativeExecuteCommand

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any


def coord_to_cm(coord: float, *, in_mm: bool) -> int:
    """Validate and convert coordinate to integer native cm."""
    if isinstance(coord, bool) or not isinstance(coord, (int, float)):
        msg = f"Coordinate must be a numeric type: {coord}"
        raise TypeError(msg)
    if not math.isfinite(coord):
        msg = f"Coordinate must be finite: {coord}"
        raise ValueError(msg)
    if in_mm:
        if coord % 10 != 0:
            msg = (
                f"Coordinate {coord} mm has fractional centimeter component; "
                "must be aligned to 10 mm"
            )
            raise ValueError(msg)
        return int(coord // 10)
    if isinstance(coord, float) and not coord.is_integer():
        msg = f"Native coordinate in cm must be an integer: {coord}"
        raise ValueError(msg)
    return int(coord)


def build_add_overlay_args(
    kind: MapSetType,
    map_id: str,
    coordinates: Sequence[int | float],
    *,
    in_mm: bool,
) -> dict[str, Any]:
    """Build body arguments for adding a map overlay."""
    coords_cm = [coord_to_cm(c, in_mm=in_mm) for c in coordinates]
    mode = 1 if kind == MapSetType.VIRTUAL_WALLS else 2
    if kind == MapSetType.VIRTUAL_WALLS:
        if len(coords_cm) != 4:
            msg = (
                "Virtual wall requires exactly 4 coordinates [x1, y1, x2, y2], "
                f"got {len(coords_cm)}"
            )
            raise ValueError(msg)
        if coords_cm[0] == coords_cm[2] and coords_cm[1] == coords_cm[3]:
            msg = "Virtual wall cannot be degenerate (zero length)"
            raise ValueError(msg)
    elif len(coords_cm) < 6 or len(coords_cm) % 2 != 0:
        msg = (
            "Restricted zone requires at least 3 points (6 coordinates) "
            f"with even length, got {len(coords_cm)}"
        )
        raise ValueError(msg)
    elif min(coords_cm[0::2]) == max(coords_cm[0::2]) or min(coords_cm[1::2]) == max(
        coords_cm[1::2]
    ):
        msg = "Restricted zone polygon cannot be degenerate"
        raise ValueError(msg)

    return {
        "action": "add",
        "mode": mode,
        "type": mode,
        "mapId": map_id,
        "point": ",".join(str(c) for c in coords_cm),
    }


class NativeCleanRoom(NativeExecuteCommand):
    """Clean specific rooms by ID (opcode 40007)."""

    NAME = "40007"

    def __init__(self, room_ids: Sequence[int]) -> None:
        if not room_ids:
            msg = "Room IDs list cannot be empty"
            raise ValueError(msg)

        validated: list[int] = []
        for rid in room_ids:
            if isinstance(rid, bool) or not isinstance(rid, int):
                msg = f"Room ID must be a non-boolean integer: {rid}"
                raise TypeError(msg)
            if rid <= 0:
                msg = f"Room ID must be a positive integer: {rid}"
                raise ValueError(msg)
            validated.append(rid)

        super().__init__(
            {
                "cleanSwitch": True,
                "cleanMode": "area",
                "cleanValues": validated,
            }
        )


class NativeCleanZone(NativeExecuteCommand):
    """Clean a custom rectangular zone (opcode 40005)."""

    NAME = "40005"

    def __init__(self, clean_values: Sequence[int]) -> None:
        if len(clean_values) != 8:
            msg = (
                "Zone cleanValues requires exactly 8 signed integer coordinates, "
                f"got {len(clean_values)}"
            )
            raise ValueError(msg)

        validated: list[int] = []
        for val in clean_values:
            if isinstance(val, bool) or not isinstance(val, int):
                msg = f"Coordinate must be a non-boolean integer: {val}"
                raise TypeError(msg)
            validated.append(val)

        p0_x, p0_y, p1_x, p1_y, p2_x, p2_y, p3_x, p3_y = validated
        if not (p0_x == p1_x and p2_x == p3_x and p1_y == p2_y and p0_y == p3_y):
            msg = "Coordinates do not match Cartesian bounding polygon corner sequence"
            raise ValueError(msg)
        if p0_x >= p2_x or p1_y >= p0_y:
            msg = "Degenerate zone rectangle: xmin < xmax and ymin < ymax required"
            raise ValueError(msg)

        super().__init__(
            {
                "cleanSwitch": True,
                "cleanMode": "zone",
                "cleanValues": validated,
            }
        )

    @classmethod
    def from_bounds(cls, xmin: int, ymin: int, xmax: int, ymax: int) -> NativeCleanZone:
        """Create zone command from Cartesian bounding limits."""
        return cls([xmin, ymax, xmin, ymin, xmax, ymin, xmax, ymax])


def native_clean_area(
    mode: CleanMode,
    area: Sequence[int | float],
    cleanings: int = 1,
) -> NativeExecuteCommand:
    """Create concrete native command for room or zone cleaning."""
    if cleanings != 1:
        msg = (
            f"Repetition count {cleanings} is not supported by native clean commands. "
            "Only cleanings=1 is allowed."
        )
        raise ValueError(msg)

    match mode:
        case CleanMode.SPOT_AREA:
            if not area:
                msg = "Room IDs list cannot be empty"
                raise ValueError(msg)
            room_ids: list[int] = []
            for item in area:
                if isinstance(item, bool) or not isinstance(item, int):
                    msg = f"Room ID must be a non-boolean integer: {item}"
                    raise TypeError(msg)
                room_ids.append(item)
            return NativeCleanRoom(room_ids)

        case CleanMode.CUSTOM_AREA:
            if len(area) != 4:
                msg = (
                    "Custom area requires exactly 4 diagonal coordinates [x1, y1, x2, y2], "
                    f"got {len(area)}"
                )
                raise ValueError(msg)
            coords_cm = [coord_to_cm(c, in_mm=True) for c in area]
            x1, y1, x2, y2 = coords_cm
            xmin, xmax = min(x1, x2), max(x1, x2)
            ymin, ymax = min(y1, y2), max(y1, y2)
            if xmin == xmax or ymin == ymax:
                msg = "Degenerate rectangle: width and height must be non-zero"
                raise ValueError(msg)
            return NativeCleanZone.from_bounds(xmin, ymin, xmax, ymax)

        case CleanMode.AUTO | CleanMode.FREE_CLEAN:
            msg = f"CleanMode {mode} is not supported for native clean area"
            raise ValueError(msg)
