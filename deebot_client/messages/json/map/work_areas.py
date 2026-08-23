"""Read-only GOAT O1200 work-area snapshot handling."""

from __future__ import annotations

import binascii
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Final
from weakref import WeakKeyDictionary

import orjson

from deebot_client.events.map import (
    MowerMapTraceGroup,
    MowerMapTraceSegment,
    MowerStaticMapEvent,
    MowerWorkArea,
    MowerWorkAreasEvent,
)
from deebot_client.message import (
    HandlingResult,
    HandlingState,
    MessageBody,
    MessageBodyDataDict,
)

from .o1200 import (
    OBSERVED_DIRECTION_STEP,
    O1200RlePath,
    canonical_decimal,
    decode_trimmed_lzma_bytes,
    parse_rle_path,
    strict_base64_decode,
)

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_MAX_ON_ARI_SEGMENTS: Final = 16
_MAX_COMPRESSED_BYTES: Final = 524_288
_MAX_AREA_SET_DECOMPRESSED_BYTES: Final = 1_048_576
_MAX_IN_FLIGHT_SNAPSHOTS: Final = 16
_MAX_REGISTRATION_COMPARISONS: Final = 10_000_000


@dataclass(frozen=True)
class _OnArIIdentity:
    mid: str
    batid: str = field(repr=False)
    serial: int
    info_size: int
    type_value: int
    using: int


_ON_ARI_CHUNK_BUFFER: dict[_OnArIIdentity, dict[int, bytes]] = {}


@dataclass(frozen=True)
class _AreaGeometry:
    area_id: str
    path: O1200RlePath
    raw: str


@dataclass(frozen=True)
class _OnArISnapshot:
    mid: str
    areas: tuple[_AreaGeometry, ...]


@dataclass(frozen=True)
class _AreaMetadata:
    area_id: str
    name: str


@dataclass(frozen=True)
class _AreaSetSnapshot:
    mid: str
    areas: tuple[_AreaMetadata, ...]


@dataclass(frozen=True)
class _Registration:
    main_index: int
    area_index: int
    matched_direction_count: int
    offset_x: int
    offset_y: int


class _MowerWorkAreaCoordinator:
    """Join complete read-only snapshots without appending stale areas."""

    def __init__(self) -> None:
        self._static_maps: dict[str, MowerStaticMapEvent] = {}
        self._geometry: dict[str, _OnArISnapshot] = {}
        self._metadata: dict[str, _AreaSetSnapshot] = {}

    def update_static_map(
        self, snapshot: MowerStaticMapEvent
    ) -> MowerWorkAreasEvent | None:
        """Replace one static-map snapshot and attempt a complete join."""
        self._static_maps[snapshot.mid] = snapshot
        return self._build(snapshot.mid)

    def update_geometry(self, snapshot: _OnArISnapshot) -> MowerWorkAreasEvent | None:
        """Replace one area-geometry snapshot and attempt a complete join."""
        self._geometry[snapshot.mid] = snapshot
        return self._build(snapshot.mid)

    def update_metadata(self, snapshot: _AreaSetSnapshot) -> MowerWorkAreasEvent | None:
        """Replace one area-metadata snapshot and attempt a complete join."""
        self._metadata[snapshot.mid] = snapshot
        return self._build(snapshot.mid)

    def _build(self, mid: str) -> MowerWorkAreasEvent | None:
        static_map = self._static_maps.get(mid)
        geometry = self._geometry.get(mid)
        metadata = self._metadata.get(mid)
        if static_map is None or geometry is None or metadata is None:
            return None
        if static_map.step_size != OBSERVED_DIRECTION_STEP:
            return None

        geometry_by_id = {area.area_id: area for area in geometry.areas}
        metadata_by_id = {area.area_id: area for area in metadata.areas}
        if (
            len(geometry_by_id) != len(geometry.areas)
            or len(metadata_by_id) != len(metadata.areas)
            or geometry_by_id.keys() != metadata_by_id.keys()
        ):
            return None

        main_path = _extract_main_path(static_map)
        if main_path is None:
            return None

        areas: list[MowerWorkArea] = []
        for local_area in geometry.areas:
            registered = _register_area(main_path, local_area)
            if registered is None:
                return None
            areas.append(
                MowerWorkArea(
                    name=metadata_by_id[local_area.area_id].name,
                    geometry=registered,
                )
            )

        return MowerWorkAreasEvent(
            mid=mid,
            areas=areas,
            step_size=OBSERVED_DIRECTION_STEP,
        )


_COORDINATORS: WeakKeyDictionary[object, _MowerWorkAreaCoordinator] = (
    WeakKeyDictionary()
)


def _coordinator_for(event_bus: EventBus) -> _MowerWorkAreaCoordinator:
    coordinator = _COORDINATORS.get(event_bus)
    if coordinator is None:
        coordinator = _MowerWorkAreaCoordinator()
        _COORDINATORS[event_bus] = coordinator
    return coordinator


def update_static_map_snapshot(
    event_bus: EventBus, snapshot: MowerStaticMapEvent
) -> None:
    """Update the latest static snapshot and emit a completed join if possible."""
    if event := _coordinator_for(event_bus).update_static_map(snapshot):
        event_bus.notify(event)


def _update_geometry_snapshot(event_bus: EventBus, snapshot: _OnArISnapshot) -> None:
    if event := _coordinator_for(event_bus).update_geometry(snapshot):
        event_bus.notify(event)


def _update_metadata_snapshot(event_bus: EventBus, snapshot: _AreaSetSnapshot) -> None:
    if event := _coordinator_for(event_bus).update_metadata(snapshot):
        event_bus.notify(event)


class OnArI(MessageBodyDataDict):
    """Parse complete observed O1200 type-0 work-area geometry snapshots."""

    NAME = "onArI"
    _CHUNK_BUFFER: ClassVar[dict[_OnArIIdentity, dict[int, bytes]]] = (
        _ON_ARI_CHUNK_BUFFER
    )

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Buffer one validated segment and publish only complete snapshots."""
        type_value = canonical_decimal(data.get("type"))
        if type_value != 0:
            return HandlingResult.success()

        try:
            snapshot = cls._accept_segment(data)
        except (
            binascii.Error,
            orjson.JSONDecodeError,
            RuntimeError,
            TypeError,
            UnicodeEncodeError,
            ValueError,
        ):
            return _analyse_without_payload_log()

        if snapshot is not None:
            _update_geometry_snapshot(event_bus, snapshot)
        return HandlingResult.success()

    @classmethod
    def _accept_segment(cls, data: dict[str, Any]) -> _OnArISnapshot | None:
        mid = data.get("mid")
        batid = data.get("batid")
        serial = canonical_decimal(data.get("serial"))
        index = canonical_decimal(data.get("index"))
        info_size = canonical_decimal(data.get("infoSize"))
        type_value = canonical_decimal(data.get("type"))
        using = canonical_decimal(data.get("using"))
        info = data.get("info")
        if (
            not isinstance(mid, str)
            or not mid
            or not isinstance(batid, str)
            or not batid
            or serial is None
            or not 0 < serial <= _MAX_ON_ARI_SEGMENTS
            or index is None
            or not 0 <= index < serial
            or info_size is None
            or info_size <= 0
            or type_value != 0
            or using != 1
            or not isinstance(info, str)
        ):
            raise ValueError("Unsupported onArI envelope")

        identity = _OnArIIdentity(
            mid=mid,
            batid=batid,
            serial=serial,
            info_size=info_size,
            type_value=type_value,
            using=using,
        )
        cycle = (mid, batid, type_value, using)
        conflicting = [
            key
            for key in cls._CHUNK_BUFFER
            if (key.mid, key.batid, key.type_value, key.using) == cycle
            and key != identity
        ]
        if conflicting:
            for key in conflicting:
                cls._CHUNK_BUFFER.pop(key, None)
            raise ValueError("Mixed onArI envelope identity")

        chunk = strict_base64_decode(info)
        if not chunk:
            raise ValueError("Empty onArI segment")
        if (
            identity not in cls._CHUNK_BUFFER
            and len(cls._CHUNK_BUFFER) >= _MAX_IN_FLIGHT_SNAPSHOTS
        ):
            cls._CHUNK_BUFFER.pop(next(iter(cls._CHUNK_BUFFER)))
        parts = cls._CHUNK_BUFFER.setdefault(identity, {})
        if index in parts:
            cls._CHUNK_BUFFER.pop(identity, None)
            raise ValueError("Duplicate onArI index")
        if (
            sum(len(value) for value in parts.values()) + len(chunk)
            > _MAX_COMPRESSED_BYTES
        ):
            cls._CHUNK_BUFFER.pop(identity, None)
            raise ValueError("onArI compressed-size limit exceeded")
        parts[index] = chunk

        expected_indexes = set(range(serial))
        if set(parts) != expected_indexes:
            return None

        compressed = b"".join(parts[index] for index in range(serial))
        cls._CHUNK_BUFFER.pop(identity, None)
        decoded = decode_trimmed_lzma_bytes(compressed, info_size=info_size)
        return _parse_on_ari_snapshot(decoded, expected_mid=mid)


class GetAreaSet(MessageBody):
    """Parse read-only observed O1200 getAreaSet type-ar responses."""

    NAME = "getAreaSet"

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """Publish one metadata snapshot without exposing opaque row fields."""
        data = body.get("data")
        if not isinstance(data, dict):
            return _analyse_without_payload_log()
        if data.get("type") != "ar":
            return HandlingResult.success()
        if body.get("code") != 0:
            return _analyse_without_payload_log()

        try:
            snapshot = _parse_area_set_snapshot(data)
        except (
            binascii.Error,
            orjson.JSONDecodeError,
            RuntimeError,
            TypeError,
            UnicodeEncodeError,
            ValueError,
        ):
            return _analyse_without_payload_log()

        _update_metadata_snapshot(event_bus, snapshot)
        return HandlingResult.success()


def _parse_on_ari_snapshot(decoded: bytes, *, expected_mid: str) -> _OnArISnapshot:
    document = orjson.loads(decoded)
    if not isinstance(document, list) or not document:
        raise ValueError("Unsupported onArI JSON document")

    layer_one: list[Any] | None = None
    for group in document:
        if (
            not isinstance(group, list)
            or len(group) < 3
            or not isinstance(group[0], str)
            or not isinstance(group[1], str)
            or group[0] != expected_mid
        ):
            raise ValueError("Unsupported onArI outer group")
        if group[1] == "1":
            if layer_one is not None:
                raise ValueError("Duplicate onArI layer 1")
            layer_one = group

    if layer_one is None or len(layer_one) == 3:
        raise ValueError("Missing onArI layer-1 records")

    areas: list[_AreaGeometry] = []
    seen_ids: set[str] = set()
    for raw_record in layer_one[3:]:
        if not isinstance(raw_record, str):
            raise TypeError("Unsupported onArI layer-1 record")
        try:
            area_id, start, encoded_rle = raw_record.split(";")
        except ValueError as error:
            raise ValueError("Unsupported onArI layer-1 record") from error
        if not area_id or area_id in seen_ids:
            raise ValueError("Duplicate or empty onArI area ID")
        seen_ids.add(area_id)
        areas.append(
            _AreaGeometry(
                area_id=area_id,
                path=parse_rle_path(start, encoded_rle),
                raw=raw_record,
            )
        )
    return _OnArISnapshot(mid=expected_mid, areas=tuple(areas))


def _parse_area_set_snapshot(data: dict[str, Any]) -> _AreaSetSnapshot:
    mid = data.get("mid")
    info_size = canonical_decimal(data.get("infoSize"))
    subsets = data.get("subsets")
    if (
        data.get("type") != "ar"
        or not isinstance(mid, str)
        or not mid
        or info_size is None
        or info_size <= 0
        or not isinstance(subsets, str)
    ):
        raise ValueError("Unsupported getAreaSet envelope")

    # Unlike the observed onMI/onArI framing, AreaSet envelope ``infoSize`` is
    # not the decompressed byte length. Keep it validated as opaque envelope
    # metadata and use the trimmed LZMA-Alone header's own size instead.
    decoded = _decode_area_set_subsets(subsets)
    rows = orjson.loads(decoded)
    if not isinstance(rows, list) or not rows:
        raise ValueError("Unsupported getAreaSet rows")

    areas: list[_AreaMetadata] = []
    seen_ids: set[str] = set()
    for row in rows:
        if (
            not isinstance(row, list)
            or len(row) < 7
            or not isinstance(row[0], str)
            or not isinstance(row[1], str)
            or not isinstance(row[2], str)
            or row[0] != mid
            or not row[1]
            or row[1] in seen_ids
        ):
            raise ValueError("Unsupported getAreaSet row")
        seen_ids.add(row[1])
        areas.append(_AreaMetadata(area_id=row[1], name=row[2]))
    return _AreaSetSnapshot(mid=mid, areas=tuple(areas))


def _decode_area_set_subsets(value: str) -> bytes:
    compressed = strict_base64_decode(value)
    if len(compressed) > _MAX_COMPRESSED_BYTES:
        raise ValueError("getAreaSet compressed-size limit exceeded")
    if len(compressed) < 9:
        raise ValueError("Unsupported getAreaSet trimmed LZMA-Alone framing")

    decompressed_size = int.from_bytes(compressed[5:9], "little")
    if not 0 < decompressed_size <= _MAX_AREA_SET_DECOMPRESSED_BYTES:
        raise ValueError("Unsupported getAreaSet decompressed-size header")
    return decode_trimmed_lzma_bytes(compressed, info_size=decompressed_size)


def _extract_main_path(static_map: MowerStaticMapEvent) -> O1200RlePath | None:
    candidates: list[O1200RlePath] = []
    for group in static_map.groups:
        for segment in group.segments:
            if segment.raw is None:
                continue
            try:
                object_id, segment_mid, start, encoded_rle = segment.raw.split(";", 3)
            except ValueError:
                continue
            if object_id != "s1" or segment_mid != static_map.mid:
                continue
            try:
                path = parse_rle_path(start, encoded_rle)
            except ValueError:
                return None
            if path.points != segment.points:
                return None
            candidates.append(path)
    return candidates[0] if len(candidates) == 1 else None


def _register_area(
    main_path: O1200RlePath, area: _AreaGeometry
) -> MowerMapTraceGroup | None:
    registration = _find_registration(main_path, area.path)
    if registration is None:
        return None
    translated = [
        (x + registration.offset_x, y + registration.offset_y)
        for x, y in area.path.points
    ]
    return MowerMapTraceGroup(
        group_id=area.area_id,
        segments=[MowerMapTraceSegment(points=translated, raw=area.raw)],
    )


def _find_registration(
    main_path: O1200RlePath, area_path: O1200RlePath
) -> _Registration | None:
    main = main_path.directions
    area = area_path.directions
    if not main or not area or len(main) * len(area) > _MAX_REGISTRATION_COMPARISONS:
        return None

    matched_count = _longest_shared_direction_count(main, area)
    if matched_count == 0:
        return None

    previous = [0] * (len(area) + 1)
    translation: tuple[int, int] | None = None
    selected: tuple[int, int] | None = None
    for main_end, main_direction in enumerate(main, 1):
        current = [0] * (len(area) + 1)
        for area_end, area_direction in enumerate(area, 1):
            if main_direction != area_direction:
                continue
            current[area_end] = previous[area_end - 1] + 1
            if current[area_end] != matched_count:
                continue
            main_index = main_end - matched_count
            area_index = area_end - matched_count
            candidate = (
                main_path.points[main_index][0] - area_path.points[area_index][0],
                main_path.points[main_index][1] - area_path.points[area_index][1],
            )
            if translation is None:
                translation = candidate
                selected = (main_index, area_index)
            elif candidate != translation:
                return None
        previous = current

    if translation is None or selected is None:
        return None
    main_index, area_index = selected
    for point_offset in range(matched_count + 1):
        main_point = main_path.points[main_index + point_offset]
        area_point = area_path.points[area_index + point_offset]
        if main_point != (
            area_point[0] + translation[0],
            area_point[1] + translation[1],
        ):
            return None

    return _Registration(
        main_index=main_index,
        area_index=area_index,
        matched_direction_count=matched_count,
        offset_x=translation[0],
        offset_y=translation[1],
    )


def _longest_shared_direction_count(
    main: tuple[str, ...], area: tuple[str, ...]
) -> int:
    previous = [0] * (len(area) + 1)
    longest = 0
    for main_direction in main:
        current = [0] * (len(area) + 1)
        for area_index, area_direction in enumerate(area, 1):
            if main_direction == area_direction:
                current[area_index] = previous[area_index - 1] + 1
                longest = max(longest, current[area_index])
        previous = current
    return longest


def _analyse_without_payload_log() -> HandlingResult:
    """Fall through without logging device/session-bearing envelopes."""
    return HandlingResult(HandlingState.ANALYSE_LOGGED)


def _reset_work_area_state() -> None:
    """Reset process-local buffers for isolated tests."""
    _ON_ARI_CHUNK_BUFFER.clear()
    _COORDINATORS.clear()
