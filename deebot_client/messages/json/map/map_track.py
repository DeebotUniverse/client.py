"""Read-only GOAT O1200 onMapTrack state handling."""

from __future__ import annotations

import binascii
from dataclasses import dataclass, field
from time import monotonic
from typing import TYPE_CHECKING, Any, Final
from weakref import WeakKeyDictionary

import orjson

from deebot_client.events.map import (
    MowerMapTrackEvent,
    MowerMapTrackRecord,
    MowerMapTrackSegment,
)
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict

from .o1200 import (
    OBSERVED_DIRECTION_STEP,
    canonical_decimal,
    decode_trimmed_lzma_bytes,
    parse_coordinate,
    parse_rle_path,
    strict_base64_decode,
)

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_MAX_ON_MAP_TRACK_SEGMENTS: Final = 8
_MAX_COMPRESSED_BYTES: Final = 524_288
_MAX_DECOMPRESSED_BYTES: Final = 1_048_576
_MAX_IN_FLIGHT_BATCHES: Final = 16
_MAX_BATCH_AGE_SECONDS: Final = 120.0
_MAX_RECORDS_PER_UPDATE: Final = 1_024
_MAX_GEOMETRY_SEGMENTS_PER_RECORD: Final = 32
_MAX_POINTS_PER_RECORD: Final = 4_096
_MAX_POINTS_PER_UPDATE: Final = 16_384
_SUPPORTED_PROTOCOL_VERSION: Final = "1"
_SUPPORTED_UPDATE_TYPES: Final = {1, 2}


@dataclass(frozen=True)
class _MapTrackIdentity:
    mid: str
    batid: str = field(repr=False)
    serial: int
    info_size: int


@dataclass
class _MapTrackParts:
    chunks: dict[int, bytes] = field(default_factory=dict)
    created_at: float = field(default_factory=monotonic)


@dataclass(frozen=True)
class _MapTrackRecordChange:
    key: tuple[str, str, str]
    record: MowerMapTrackRecord | None


@dataclass(frozen=True)
class _MapTrackUpdate:
    protocol_version: str
    update_type: int
    records: tuple[_MapTrackRecordChange, ...]


class _MowerMapTrackState:
    """Replay one current map-track state for one EventBus lifecycle."""

    def __init__(self) -> None:
        self._initialized = False
        self._records: dict[tuple[str, str, str], MowerMapTrackRecord] = {}

    def apply_batch(
        self,
        *,
        mid: str,
        updates: tuple[_MapTrackUpdate, ...],
    ) -> tuple[MowerMapTrackEvent, ...]:
        initialized = self._initialized
        records = dict(self._records)
        events: list[MowerMapTrackEvent] = []

        for update in updates:
            if update.update_type == 1:
                records = {
                    change.key: change.record
                    for change in update.records
                    if change.record is not None
                }
                initialized = True
            elif update.update_type == 2:
                if not initialized:
                    continue
                for change in update.records:
                    if change.record is None:
                        records.pop(change.key, None)
                    else:
                        records[change.key] = change.record
            else:
                raise ValueError("Unsupported onMapTrack update type")

            events.append(
                MowerMapTrackEvent(
                    mid=mid,
                    protocol_version=update.protocol_version,
                    update_type=update.update_type,
                    records=_sorted_records(records),
                    step_size=OBSERVED_DIRECTION_STEP,
                )
            )

        self._initialized = initialized
        self._records = records
        return tuple(events)


@dataclass
class _MowerMapTrackParserState:
    chunks: dict[_MapTrackIdentity, _MapTrackParts] = field(default_factory=dict)
    track_state: _MowerMapTrackState = field(default_factory=_MowerMapTrackState)


_PARSER_STATES: WeakKeyDictionary[object, _MowerMapTrackParserState] = (
    WeakKeyDictionary()
)


class OnMapTrack(MessageBodyDataDict):
    """Parse complete GOAT O1200 map-track snapshots and patches."""

    NAME = "onMapTrack"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Buffer one validated segment and publish only complete updates."""
        parser_state = _parser_state_for(event_bus)
        try:
            batch = cls._accept_segment(parser_state, data)
        except (
            binascii.Error,
            orjson.JSONDecodeError,
            RuntimeError,
            TypeError,
            UnicodeEncodeError,
            ValueError,
        ):
            return _analyse_without_payload_log()

        if batch is None:
            return HandlingResult.success()

        identity, decoded = batch
        try:
            updates = tuple(_parse_updates(decoded))
            events = parser_state.track_state.apply_batch(
                mid=identity.mid, updates=updates
            )
        except orjson.JSONDecodeError, TypeError, ValueError:
            return _analyse_without_payload_log()

        for event in events:
            event_bus.notify(event)
        return HandlingResult.success()

    @classmethod
    def _accept_segment(
        cls, parser_state: _MowerMapTrackParserState, data: dict[str, Any]
    ) -> tuple[_MapTrackIdentity, bytes] | None:
        _prune_stale(parser_state.chunks, monotonic())

        mid = data.get("mid")
        batid = data.get("batid")
        serial = canonical_decimal(data.get("serial"))
        index = canonical_decimal(data.get("index"))
        info_size = canonical_decimal(data.get("infoSize"))
        info = data.get("info")
        if (
            not isinstance(mid, str)
            or not mid
            or not isinstance(batid, str)
            or not batid
            or serial is None
            or not 0 < serial <= _MAX_ON_MAP_TRACK_SEGMENTS
            or index is None
            or not 0 <= index < serial
            or info_size is None
            or not 0 < info_size <= _MAX_DECOMPRESSED_BYTES
            or not isinstance(info, str)
        ):
            raise ValueError("Unsupported onMapTrack segment envelope")

        identity = _MapTrackIdentity(
            mid=mid,
            batid=batid,
            serial=serial,
            info_size=info_size,
        )
        _reject_conflicting_transfer(parser_state.chunks, identity)
        chunk = strict_base64_decode(info)
        if not chunk:
            raise ValueError("Empty onMapTrack segment")
        if (
            identity not in parser_state.chunks
            and len(parser_state.chunks) >= _MAX_IN_FLIGHT_BATCHES
        ):
            parser_state.chunks.pop(next(iter(parser_state.chunks)))
        parts = parser_state.chunks.setdefault(identity, _MapTrackParts())
        if index in parts.chunks:
            parser_state.chunks.pop(identity, None)
            raise ValueError("Duplicate onMapTrack index")
        if (
            sum(len(value) for value in parts.chunks.values()) + len(chunk)
            > _MAX_COMPRESSED_BYTES
        ):
            parser_state.chunks.pop(identity, None)
            raise ValueError("onMapTrack compressed-size limit exceeded")
        parts.chunks[index] = chunk

        if set(parts.chunks) != set(range(serial)):
            return None

        compressed = b"".join(parts.chunks[index] for index in range(serial))
        parser_state.chunks.pop(identity, None)
        decoded = decode_trimmed_lzma_bytes(compressed, info_size=info_size)
        return identity, decoded


def _parser_state_for(event_bus: EventBus) -> _MowerMapTrackParserState:
    state = _PARSER_STATES.get(event_bus)
    if state is None:
        state = _MowerMapTrackParserState()
        _PARSER_STATES[event_bus] = state
    return state


def _prune_stale(chunks: dict[_MapTrackIdentity, _MapTrackParts], now: float) -> None:
    stale = [
        identity
        for identity, parts in chunks.items()
        if now - parts.created_at > _MAX_BATCH_AGE_SECONDS
    ]
    for identity in stale:
        chunks.pop(identity, None)


def _reject_conflicting_transfer(
    buffer: dict[_MapTrackIdentity, _MapTrackParts],
    identity: _MapTrackIdentity,
) -> None:
    cycle = (identity.mid, identity.batid)
    conflicting = [
        key for key in buffer if (key.mid, key.batid) == cycle and key != identity
    ]
    if conflicting:
        for key in conflicting:
            buffer.pop(key, None)
        raise ValueError("Mixed onMapTrack envelope identity")


def _parse_updates(decoded: bytes) -> list[_MapTrackUpdate]:
    document = orjson.loads(decoded)
    if not isinstance(document, list) or not document:
        raise ValueError("Unsupported onMapTrack JSON document")

    updates: list[_MapTrackUpdate] = []
    for outer in document:
        if (
            not isinstance(outer, list)
            or len(outer) < 2
            or not isinstance(outer[0], str)
        ):
            raise ValueError("Unsupported onMapTrack outer group")
        protocol_version = outer[0]
        update_type = canonical_decimal(outer[1])
        if (
            protocol_version != _SUPPORTED_PROTOCOL_VERSION
            or update_type not in _SUPPORTED_UPDATE_TYPES
        ):
            raise ValueError("Unsupported onMapTrack protocol/update type")
        raw_records = tuple(outer[2:])
        if len(raw_records) > _MAX_RECORDS_PER_UPDATE:
            raise ValueError("onMapTrack record limit exceeded")
        if any(not isinstance(record, str) for record in raw_records):
            raise TypeError("Unsupported onMapTrack record value")

        parsed = tuple(_parse_record(record) for record in raw_records)
        _check_update_point_budget(parsed)
        updates.append(
            _MapTrackUpdate(
                protocol_version=protocol_version,
                update_type=update_type,
                records=parsed,
            )
        )
    return updates


def _parse_record(raw: str) -> _MapTrackRecordChange:
    key = _record_key(raw)
    fields = raw.split(";")
    if len(fields) == 3:
        return _MapTrackRecordChange(key=key, record=None)

    geometry_fields = _geometry_fields(fields[3:])
    segments, geometry_encoding = _parse_geometry_segments(geometry_fields)
    return _MapTrackRecordChange(
        key=key,
        record=MowerMapTrackRecord(
            key=key,
            raw=raw,
            segments=segments,
            geometry_encoding=geometry_encoding,
        ),
    )


def _geometry_fields(fields: list[str]) -> tuple[str, ...]:
    while fields and fields[-1] == "":
        fields.pop()
    if not fields or any(not field for field in fields):
        raise ValueError("Empty onMapTrack geometry")
    return tuple(fields)


def _parse_geometry_segments(
    fields: tuple[str, ...],
) -> tuple[tuple[MowerMapTrackSegment, ...], str]:
    if all(_is_coordinate(field) for field in fields):
        points = tuple(parse_coordinate(field) for field in fields)
        _check_record_point_budget(len(points))
        return (MowerMapTrackSegment(points=points),), "points"

    segments: list[MowerMapTrackSegment] = []
    current_points: list[tuple[int, int]] = []
    current_points_count = 0
    last_was_rle = False

    for geometry_field in fields:
        if _is_coordinate(geometry_field):
            point = parse_coordinate(geometry_field)
            if current_points and last_was_rle:
                segments.append(MowerMapTrackSegment(points=tuple(current_points)))
                if len(segments) > _MAX_GEOMETRY_SEGMENTS_PER_RECORD:
                    raise ValueError("onMapTrack segment limit exceeded")
                current_points = []
            current_points_count += 1
            _check_record_point_budget(current_points_count)
            current_points.append(point)
            last_was_rle = False
            continue

        if not current_points:
            raise ValueError("Unsupported onMapTrack RLE geometry")

        path = parse_rle_path(_format_point(current_points[-1]), geometry_field)
        added_points = path.points[1:]
        current_points_count += len(added_points)
        _check_record_point_budget(current_points_count)
        current_points.extend(added_points)
        last_was_rle = True

    if current_points:
        segments.append(MowerMapTrackSegment(points=tuple(current_points)))
    if not segments or len(segments) > _MAX_GEOMETRY_SEGMENTS_PER_RECORD:
        raise ValueError("onMapTrack segment limit exceeded")
    return tuple(segments), "rle"


def _check_record_point_budget(point_count: int) -> None:
    if point_count > _MAX_POINTS_PER_RECORD:
        raise ValueError("onMapTrack record point limit exceeded")


def _check_update_point_budget(records: tuple[_MapTrackRecordChange, ...]) -> None:
    point_count = 0
    for change in records:
        if change.record is None:
            continue
        point_count += sum(len(segment.points) for segment in change.record.segments)
        if point_count > _MAX_POINTS_PER_UPDATE:
            raise ValueError("onMapTrack update point limit exceeded")


def _record_key(record: str) -> tuple[str, str, str]:
    fields = record.split(";")
    if len(fields) < 3 or not fields[0] or not fields[1] or not fields[2]:
        raise ValueError("Unsupported onMapTrack record key")
    return fields[0], fields[1], fields[2]


def _is_coordinate(value: str) -> bool:
    try:
        parse_coordinate(value)
    except ValueError:
        return False
    return True


def _format_point(point: tuple[int, int]) -> str:
    return f"{point[0]},{point[1]}"


def _sorted_records(
    records: dict[tuple[str, str, str], MowerMapTrackRecord],
) -> tuple[MowerMapTrackRecord, ...]:
    return tuple(records[key] for key in sorted(records))


def _analyse_without_payload_log() -> HandlingResult:
    """Fall through without recording device/session-bearing envelopes."""
    return HandlingResult(HandlingState.ANALYSE_LOGGED)


def _reset_map_track_state() -> None:
    """Reset process-local parser lifecycles for isolated tests."""
    _PARSER_STATES.clear()
