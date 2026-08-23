"""Map messages."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any, ClassVar

import orjson

from deebot_client.events.map import (
    MajorMapEvent,
    MapInfoEvent,
    MapSetType,
    MapTraceEvent,
    MowerMapTraceEvent,
    MowerMapTraceGroup,
    MowerMapTraceSegment,
)
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict
from deebot_client.rs.util import decompress_base64_data

from .cached_map_info import OnCachedMapInfo
from .on_mi import OnMI
from .work_areas import GetAreaSet, OnArI

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)

__all__ = [
    "GetAreaSet",
    "OnArI",
    "OnCachedMapInfo",
    "OnMI",
    "OnMajorMap",
    "OnMapInfoV2",
    "OnMapSetV2",
    "OnMapTrace",
]


class OnMapSetV2(MessageBodyDataDict):
    """On map set v2 message."""

    NAME = "onMapSet_V2"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # check if type is know and mid us given
        if not MapSetType.has_value(data["type"]) or not data.get("mid"):
            return HandlingResult.analyse()

        commands = []
        if map_cap := event_bus.capabilities.map:
            commands.append(map_cap.set.execute(data["mid"], MapSetType(data["type"])))

        return HandlingResult(HandlingState.SUCCESS, requested_commands=commands)


class OnMajorMap(MessageBodyDataDict):
    """On major map message."""

    NAME = "onMajorMap"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        values = [int(value) for value in data["value"].split(",") if value]
        map_id = data["mid"]

        event_bus.notify(MajorMapEvent(map_id, values, requested=False))

        return HandlingResult(
            HandlingState.SUCCESS,
            {"map_id": map_id, "values": values},
        )


class OnMapInfoV2(MessageBodyDataDict):
    """On map info v2 command."""

    NAME = "onMapInfo_V2"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if (outline_version := data.get("outlineVer")) == "0":
            # Skip it as it will be sent for non-active maps
            return HandlingResult.success()
        if outline_version != "1":
            # Unsupported version
            return HandlingResult.analyse()

        event_bus.notify(MapInfoEvent(map_id=data["mid"], info=data["info"]))

        return HandlingResult.success()


class OnMapTrace(MessageBodyDataDict):
    """On map trace message — variant pushed by mower firmwares (e.g. GOAT 1.15.x).

    The vacuum-style ``getMapTrace`` response carried ``traceValue`` directly.
    Mower firmwares instead push a compressed envelope that may be split
    across several ``index`` chunks of one contiguous LZMA stream:

    .. code-block:: json

        {
            "mid": "...", "batid": "...", "serial": "1",
            "index": "0", "type": "4",
            "info": "<base64 of one chunk of LZMA-compressed JSON>",
            "infoSize": 3455
        }

    Only ``index == 0`` carries the LZMA header; later indices contain
    continuation bytes and cannot be decompressed independently. We
    buffer chunks keyed by ``(mid, batid, serial, type)`` until the
    decompressed payload reaches ``infoSize`` bytes (per monsivar's
    O1200 LiDAR Pro capture analysis in DeebotUniverse/client.py#1567).

    The decompressed payload is a JSON document of the form
    ``[[group_id, "0;x1,y1;x2,y2;...", ...], ...]``. We preserve the
    group/segment structure in :class:`MowerMapTraceEvent` and also
    emit a flattened :class:`MapTraceEvent` for legacy consumers (the
    Rust ``Map`` helper) that expect a single ``"x,y;x,y;..."`` string.

    The leading ``"0"`` of each segment is treated as a segment-start
    marker and dropped from the flat representation; the segment
    boundary itself is preserved in the structured event.

    Used in lieu of the legacy ``GetMapTrace`` fallback for these devices.
    """

    NAME = "onMapTrace"

    # Bounded reassembly buffer for chunked LZMA streams.
    # Key: (mid, batid, serial, type). Value: dict[index, raw bytes].
    # Class-level so chunks survive across separate message dispatches.
    _CHUNK_BUFFER: ClassVar[dict[tuple[str, str, str, str], dict[int, bytes]]] = {}

    # Safety caps. A single trace cycle in practice is well under 100 kB
    # decompressed; these guard against firmware buggy enough to never
    # send the final chunk and pin memory forever.
    _MAX_BYTES_PER_KEY = 524_288  # 512 kB compressed per cycle
    _MAX_TOTAL_BYTES = 2_097_152  # 2 MB across all in-flight cycles
    _MAX_KEYS_TRACKED = 16  # evict oldest cycle when more than this

    # MapTraceEvent.start carries no real meaning beyond "is this a reset"
    # for the Rust Map helper: start==0 clears the trace, anything else
    # appends. Use a stable constant >0 so a mower never accidentally
    # nukes its own accumulated trace. (Previously this was overloaded
    # with ``serial``, which the firmware reuses across batches — fixed
    # per monsivar's #1567 review.)
    _COMPAT_TRACE_START = 1

    @classmethod
    def _evict_to_make_room(cls, incoming: int) -> None:
        """Drop oldest cycle(s) until adding ``incoming`` bytes fits within caps."""
        if len(cls._CHUNK_BUFFER) >= cls._MAX_KEYS_TRACKED:
            for key in list(cls._CHUNK_BUFFER.keys())[
                : len(cls._CHUNK_BUFFER) - cls._MAX_KEYS_TRACKED + 1
            ]:
                cls._CHUNK_BUFFER.pop(key, None)

        def _total() -> int:
            return sum(
                len(b) for chunks in cls._CHUNK_BUFFER.values() for b in chunks.values()
            )

        while _total() + incoming > cls._MAX_TOTAL_BYTES and cls._CHUNK_BUFFER:
            oldest = next(iter(cls._CHUNK_BUFFER))
            cls._CHUNK_BUFFER.pop(oldest, None)

    @classmethod
    def _assemble_and_decompress(
        cls,
        key: tuple[str, str, str, str],
        info_size: int,
    ) -> bytes | None:
        """Try to decompress the currently buffered chunks for ``key``.

        Returns the decompressed payload if it now matches ``infoSize``,
        otherwise ``None`` (more chunks expected). On any decoder error
        we also return ``None`` — the next chunk may complete the stream.
        """
        chunks = cls._CHUNK_BUFFER.get(key)
        if not chunks:
            return None

        sorted_idx = sorted(chunks.keys())
        # Need a contiguous prefix starting at 0 for LZMA to have its header.
        if sorted_idx[0] != 0 or sorted_idx != list(range(len(sorted_idx))):
            return None

        compressed = b"".join(chunks[i] for i in sorted_idx)
        # Re-encode to base64 because the existing Rust helper takes a
        # base64 string. The double-trip is cheap relative to LZMA itself.
        compressed_b64 = base64.b64encode(compressed).decode("ascii")
        try:
            decoded = decompress_base64_data(compressed_b64)
        except ValueError, RuntimeError:
            return None

        # Completion check: the firmware advertises the *decompressed*
        # total length via ``infoSize``. If we have less, more chunks
        # are still in flight. (If the firmware sent infoSize==0 we
        # accept anything that decompresses cleanly.)
        if info_size and len(decoded) < info_size:
            return None
        return decoded

    @staticmethod
    def _parse_groups(decoded: bytes) -> list[MowerMapTraceGroup] | None:
        """Parse the decompressed JSON into structured groups."""
        try:
            raw = orjson.loads(decoded)
        except orjson.JSONDecodeError:
            return None
        if not isinstance(raw, list):
            return None

        groups: list[MowerMapTraceGroup] = []
        for group in raw:
            if not isinstance(group, list) or len(group) < 1:
                continue
            group_id = str(group[0])
            segments: list[MowerMapTraceSegment] = []
            for raw_segment in group[1:]:
                if not isinstance(raw_segment, str):
                    continue
                # "0;x1,y1;x2,y2;..." — the leading "0" is a
                # segment-start marker, not a coordinate.
                points: list[tuple[int, int]] = []
                for raw_point in raw_segment.split(";"):
                    if not raw_point or raw_point == "0":
                        continue
                    try:
                        x_str, y_str = raw_point.split(",")
                        points.append((int(x_str), int(y_str)))
                    except ValueError:
                        continue
                if points:
                    segments.append(
                        MowerMapTraceSegment(points=points, raw=raw_segment)
                    )
            if segments:
                groups.append(MowerMapTraceGroup(group_id=group_id, segments=segments))
        return groups

    @staticmethod
    def _flatten_for_legacy(groups: list[MowerMapTraceGroup]) -> str:
        """Project structured groups onto the legacy ``"x,y;x,y;..."`` string.

        This is a lossy compatibility view: group boundaries and segment
        breaks are collapsed. Structure-aware consumers should subscribe
        to :class:`MowerMapTraceEvent` instead.
        """
        return ";".join(
            f"{x},{y}"
            for group in groups
            for segment in group.segments
            for x, y in segment.points
        )

    @classmethod
    def _handle_body_data_dict(  # noqa: PLR0911 - error-handling fan-out reads clearer as multiple returns than a state machine
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers."""
        info = data.get("info")
        if not info:
            # Not the compressed-envelope variant — leave to legacy GetMapTrace
            return HandlingResult.analyse()

        # Required envelope fields. Missing any of them → not our format.
        try:
            mid = str(data["mid"])
            batid = str(data["batid"])
            serial = str(data["serial"])
            type_ = str(data["type"])
            index = int(data["index"])
        except KeyError, TypeError, ValueError:
            _LOGGER.debug(
                "onMapTrace: missing or invalid envelope field; falling through"
            )
            return HandlingResult.analyse()

        try:
            info_size = int(data.get("infoSize", 0))
        except TypeError, ValueError:
            info_size = 0

        # ``infoSize`` is the decompressed total byte length and acts as
        # our completion signal across chunks. Without it we can't tell
        # "still buffering" from "garbage" — fall through to the legacy
        # handler.
        if info_size <= 0:
            _LOGGER.debug("onMapTrace: infoSize missing or non-positive")
            return HandlingResult.analyse()

        try:
            chunk_bytes = base64.b64decode(info)
        except ValueError, TypeError:
            _LOGGER.debug("onMapTrace: info field is not valid base64")
            return HandlingResult.analyse()

        key = (mid, batid, serial, type_)

        # A second ``index == 0`` for a key we have already seen index=0 on
        # means the firmware restarted the cycle (e.g. retry, new mowing
        # session) — drop the previous partial buffer.  Out-of-order
        # arrivals where index=0 hasn't been seen yet are preserved.
        if index == 0 and 0 in cls._CHUNK_BUFFER.get(key, {}):
            cls._CHUNK_BUFFER[key] = {}

        # Per-key cap: if adding this chunk would exceed it, the firmware
        # is misbehaving (or our parser is wrong). Drop the buffer for
        # this key rather than pinning memory.
        existing = cls._CHUNK_BUFFER.get(key, {})
        per_key_total = sum(len(b) for b in existing.values()) + len(chunk_bytes)
        if per_key_total > cls._MAX_BYTES_PER_KEY:
            # Don't log mid/batid — those identify a specific account/device
            # and CodeQL flags them as PII.
            _LOGGER.debug(
                "onMapTrace: per-key buffer cap (%d B) exceeded; dropping",
                cls._MAX_BYTES_PER_KEY,
            )
            cls._CHUNK_BUFFER.pop(key, None)
            return HandlingResult.analyse()

        cls._evict_to_make_room(len(chunk_bytes))
        cls._CHUNK_BUFFER.setdefault(key, {})[index] = chunk_bytes

        decoded = cls._assemble_and_decompress(key, info_size)
        if decoded is None:
            # More chunks expected, or the current buffer can't yet be
            # decompressed. Hold and wait for the next push.
            return HandlingResult.success()

        # We have a complete payload — release the buffer either way.
        cls._CHUNK_BUFFER.pop(key, None)

        groups = cls._parse_groups(decoded)
        if not groups:
            _LOGGER.debug("onMapTrace: decompressed payload parsed to no groups")
            return HandlingResult.analyse()

        # Structured event — preserves group_id and per-segment boundaries.
        event_bus.notify(
            MowerMapTraceEvent(
                mid=mid,
                batid=batid,
                serial=serial,
                type=type_,
                groups=groups,
            )
        )

        # Flat compatibility projection for the legacy Rust ``Map`` helper.
        # ``start`` is a non-zero constant so the Map helper appends rather
        # than clearing. (Reset semantics for mowers are handled by the
        # structure-aware consumer, not by overloading ``start``.)
        flat = cls._flatten_for_legacy(groups)
        if flat:
            event_bus.notify(
                MapTraceEvent(
                    start=cls._COMPAT_TRACE_START,
                    total=cls._COMPAT_TRACE_START,
                    data=flat,
                )
            )

        return HandlingResult.success()
