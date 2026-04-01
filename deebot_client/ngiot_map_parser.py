"""NGIOT map parser and normalization helpers.

This module converts raw NGIOT mapping payload fragments into typed Python
structures. It is intentionally conservative: it accepts partial data,
normalizes where the protocol is clear, and preserves raw fragments where the
payload shape may still vary by device or firmware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class NgiotPoint:
    """A raw or normalized point in the NGIOT map coordinate space."""

    x: int
    y: int


@dataclass(slots=True, frozen=True)
class NgiotPose:
    """Robot pose."""

    x: int
    y: int
    a: int = 0


@dataclass(slots=True, frozen=True)
class NgiotMapInfo:
    """Metadata for a single saved map."""

    map_id: str
    name: str
    using: bool
    angle: int
    charge_pos: NgiotPoint | None = None


@dataclass(slots=True, frozen=True)
class NgiotBaseMap:
    """Base map metadata and encoded raster payload."""

    map_id: str
    width: int
    height: int
    total_width: int
    total_height: int
    resolution: int
    x_min: int
    y_max: int
    encoded: str
    lz4_len: int | None = None


@dataclass(slots=True, frozen=True)
class NgiotArea:
    """Area / room / partition geometry."""

    area_id: str
    name: str | None
    polygon: list[NgiotPoint] = field(default_factory=list)
    raw: dict[str, Any] | None = None


@dataclass(slots=True, frozen=True)
class NgiotTrace:
    """Compressed trace payload metadata."""

    trace_id: str | None
    encoded: str
    lz4_len: int | None
    total_count: int
    start: int


@dataclass(slots=True, frozen=True)
class NgiotOverlay:
    """Overlay geometry such as virtual walls, mop walls, or carpets."""

    overlay_type: str
    overlay_id: str
    polygon: list[NgiotPoint] = field(default_factory=list)
    raw: dict[str, Any] | None = None


SUPPORTED_OVERLAYS: tuple[tuple[str, str], ...] = (
    ("virtual_walls", "virtualWalls"),
    ("mop_walls", "mopWalls"),
    ("carpets", "carpets"),
)


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default



def _coerce_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""



def resolve_map_id(data: dict[str, Any], fallback: str = "") -> str:
    """Resolve a map ID from a mixed NGIOT payload."""
    if (map_id := _coerce_str(data.get("mapId"))):
        return map_id

    map_data = data.get("mapData")
    if isinstance(map_data, dict) and (map_id := _coerce_str(map_data.get("mapId"))):
        return map_id

    trace_data = data.get("mapTraceData")
    if isinstance(trace_data, dict) and (map_id := _coerce_str(trace_data.get("mapId"))):
        return map_id

    return _coerce_str(fallback)



def _parse_point(value: Any) -> NgiotPoint | None:
    if not isinstance(value, dict):
        return None
    if value.get("x") is None or value.get("y") is None:
        return None
    return NgiotPoint(
        x=_coerce_int(value.get("x")),
        y=_coerce_int(value.get("y")),
    )



def _extract_point_pairs(flat_values: list[Any]) -> list[NgiotPoint]:
    points: list[NgiotPoint] = []
    ints = [_coerce_int(value) for value in flat_values]
    for index in range(0, len(ints) - 1, 2):
        points.append(NgiotPoint(x=ints[index], y=ints[index + 1]))
    return points



def _extract_polygon(raw: Any) -> list[NgiotPoint]:
    """Best-effort polygon extraction for multiple observed payload shapes."""
    if isinstance(raw, list):
        if not raw:
            return []

        if all(isinstance(item, dict) for item in raw):
            result: list[NgiotPoint] = []
            for item in raw:
                point = _parse_point(item)
                if point is not None:
                    result.append(point)
            return result

        if all(not isinstance(item, (dict, list, tuple)) for item in raw):
            return _extract_point_pairs(raw)

        result: list[NgiotPoint] = []
        for item in raw:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                result.append(NgiotPoint(x=_coerce_int(item[0]), y=_coerce_int(item[1])))
            else:
                result.extend(_extract_polygon(item))
        return result

    if isinstance(raw, dict):
        for key in (
            "points",
            "polygon",
            "coordinates",
            "coord",
            "posList",
            "vertexes",
            "vertices",
            "outline",
        ):
            if key in raw:
                return _extract_polygon(raw[key])

    return []



def parse_map_infos(data: dict[str, Any]) -> list[NgiotMapInfo]:
    """Parse map registry / mapInfos payload."""
    infos: list[NgiotMapInfo] = []
    raw_infos = data.get("mapInfos")
    if not isinstance(raw_infos, list):
        return infos

    for raw in raw_infos:
        if not isinstance(raw, dict):
            continue

        map_id = _coerce_str(raw.get("mapId"))
        if not map_id or map_id == "0":
            continue

        infos.append(
            NgiotMapInfo(
                map_id=map_id,
                name=_coerce_str(raw.get("name")),
                using=_coerce_int(raw.get("status")) == 1,
                angle=_coerce_int(raw.get("angle")),
                charge_pos=_parse_point(raw.get("chargePos")),
            )
        )

    return infos



def parse_base_map(data: dict[str, Any], map_id: str | None = None) -> NgiotBaseMap | None:
    """Parse base map metadata and encoded raster payload."""
    raw = data.get("mapData")
    if not isinstance(raw, dict):
        return None

    encoded = _coerce_str(raw.get("map")) or _coerce_str(raw.get("data"))
    if not encoded:
        return None

    resolved_map_id = _coerce_str(map_id) or resolve_map_id(data)

    return NgiotBaseMap(
        map_id=resolved_map_id,
        width=_coerce_int(raw.get("width")),
        height=_coerce_int(raw.get("height")),
        total_width=_coerce_int(raw.get("totalWidth")),
        total_height=_coerce_int(raw.get("totalHeight")),
        resolution=max(1, _coerce_int(raw.get("resolution"), 1)),
        x_min=_coerce_int(raw.get("xMin")),
        y_max=_coerce_int(raw.get("yMax")),
        encoded=encoded,
        lz4_len=_coerce_int(raw.get("lz4Len")) or None,
    )


def parse_pose(data: dict[str, Any]) -> NgiotPose | None:
    """Parse robot pose from a payload fragment."""
    raw = data.get("pos")
    if not isinstance(raw, dict):
        raw = data.get("deebotPos")
        if not isinstance(raw, dict):
            return None

    if raw.get("x") is None or raw.get("y") is None:
        return None

    return NgiotPose(
        x=_coerce_int(raw.get("x")),
        y=_coerce_int(raw.get("y")),
        a=_coerce_int(raw.get("a")),
    )



def parse_trace(data: dict[str, Any]) -> NgiotTrace | None:
    """Parse compressed map trace metadata."""
    raw = data.get("mapTraceData")
    if not isinstance(raw, dict):
        return None

    return NgiotTrace(
        trace_id=_coerce_str(raw.get("traceId")) or None,
        encoded=_coerce_str(raw.get("trace")),
        lz4_len=_coerce_int(raw.get("lz4Len")) or None,
        total_count=_coerce_int(raw.get("totalCount")),
        start=_coerce_int(raw.get("start")),
    )



def parse_areas(data: dict[str, Any]) -> list[NgiotArea]:
    """Parse room / area segmentation payload."""
    results: list[NgiotArea] = []
    raw_areas = data.get("areas")
    if not isinstance(raw_areas, list):
        return results

    for index, raw in enumerate(raw_areas):
        if not isinstance(raw, dict):
            continue

        area_id = _coerce_str(
            raw.get("id")
            or raw.get("areaId")
            or raw.get("subId")
            or raw.get("mid")
            or index
        )
        name = _coerce_str(raw.get("name") or raw.get("label")) or None
        polygon = _extract_polygon(raw)

        results.append(
            NgiotArea(
                area_id=area_id,
                name=name,
                polygon=polygon,
                raw=raw,
            )
        )

    return results



def parse_overlays(data: dict[str, Any]) -> list[NgiotOverlay]:
    """Parse overlay layers from a payload fragment."""
    results: list[NgiotOverlay] = []

    for overlay_type, field_name in SUPPORTED_OVERLAYS:
        raw_items = data.get(field_name)
        if not isinstance(raw_items, list):
            continue

        for index, raw in enumerate(raw_items):
            if not isinstance(raw, dict):
                continue

            overlay_id = _coerce_str(
                raw.get("id") or raw.get("subId") or raw.get("mid") or index
            )
            polygon = _extract_polygon(raw)

            results.append(
                NgiotOverlay(
                    overlay_type=overlay_type,
                    overlay_id=overlay_id,
                    polygon=polygon,
                    raw=raw,
                )
            )

    return results



def normalize_point(point: NgiotPoint, base_map: NgiotBaseMap) -> NgiotPoint:
    """Normalize a raw NGIOT point into map-render space."""
    return NgiotPoint(
        x=int((point.x - base_map.x_min) / base_map.resolution),
        y=int((base_map.y_max - point.y) / base_map.resolution),
    )



def normalize_pose(pose: NgiotPose, base_map: NgiotBaseMap) -> NgiotPose:
    """Normalize a raw robot pose into map-render space."""
    point = normalize_point(NgiotPoint(pose.x, pose.y), base_map)
    return NgiotPose(x=point.x, y=point.y, a=pose.a)



def normalize_polygon(points: list[NgiotPoint], base_map: NgiotBaseMap) -> list[NgiotPoint]:
    """Normalize a polygon into map-render space."""
    return [normalize_point(point, base_map) for point in points]
