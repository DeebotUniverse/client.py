"""Handler for ``onMI`` / ``onArI`` chunked mower zone map messages.

The Ecovacs GOAT A3000 LiDAR (cr0e4u) delivers zone polygon data as a
sequence of chunked MQTT ``iot/atr/onMI`` messages.  Each batch carries:

* ``batid`` — batch identifier, shared by all chunks in a delivery
* ``serial`` — total number of chunks in this batch
* ``index`` — zero-based index of this chunk (0 to serial-1)
* ``info`` — base64-encoded raw bytes for this chunk
* ``mid`` — map ID the data belongs to

All chunk payloads are concatenated in index order.  Chunk 0 has a
5-byte LZMA1 filter-properties header followed by 4 bytes (little-endian
uint32) giving the uncompressed length; remaining bytes (and all
subsequent chunks) are the raw LZMA compressed stream.

The decompressed data is a JSON array of zone entries.  Each entry maps
to one or more :class:`MapSubsetEvent` notifications so that the
integration can render zone polygons without any patching.
"""

from __future__ import annotations

import base64
import lzma
import struct
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import orjson

from deebot_client.events.map import (
    CachedMapInfoEvent,
    MapChangedEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
)
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)

# Entry type codes found in onMI payloads (empirically derived):
#   1 — mowing zone polygon
#   2 — connector path / inter-zone border
#   3 — end-of-data marker (no coordinates)
#   4 — virtual wall / no-go zone
#   5 — dock outline
_ZONE_TYPE = "1"
_NO_GO_TYPE = "4"

# Chunk buffers are module-level so they survive across multiple OnMI calls.
# Keys are batid; values track received chunks and timestamps for TTL cleanup.
_chunk_buffer: dict[str, dict[int, bytes]] = defaultdict(dict)
_chunk_meta: dict[str, dict[str, Any]] = {}  # batid -> {total, timestamp}

_CHUNK_TTL_SECONDS = 60.0

# Hard limits for on-wire header values to prevent excessive memory allocation
# from malformed payloads before the decompressor even starts.
_MAX_UNCOMPRESSED_BYTES = 4 * 1024 * 1024   # 4 MB — far exceeds any real zone map
_MAX_DICT_SIZE_BYTES = 64 * 1024 * 1024  # 64 MB — well above lzma defaults


def _cleanup_stale_batches() -> None:
    """Discard incomplete batches older than _CHUNK_TTL_SECONDS."""
    now = time.monotonic()
    stale = [
        bid
        for bid, meta in _chunk_meta.items()
        if now - meta["timestamp"] > _CHUNK_TTL_SECONDS
    ]
    for bid in stale:
        _chunk_buffer.pop(bid, None)
        _chunk_meta.pop(bid, None)
        _LOGGER.debug("onMI: discarded stale batch batid=%s", bid)


def _decode_entry(entry: Any) -> list[tuple[str, str, str]]:
    """Decode a single onMI entry into (type, zone_id, coords) tuples.

    Each entry is a list whose first element is the numeric type code
    (as an int or string) and remaining elements are coordinate strings
    of the form ``'<id>,<x1,y1;x2,y2;...>'``.

    Returns a list of ``(type_code, zone_id, coord_string)`` tuples.
    """
    if not isinstance(entry, list) or len(entry) < 1:
        return []

    type_code = str(entry[0])
    if type_code == "3":
        return []  # end-of-data marker

    results: list[tuple[str, str, str]] = []
    for field in entry[1:]:
        if not isinstance(field, str) or "," not in field:
            continue
        # Format: "<zone_id>,<x>,<y>;<x>,<y>;..."
        first_comma = field.index(",")
        zone_id = field[:first_comma]
        coords = field[first_comma + 1 :]
        if coords:
            results.append((type_code, zone_id, coords))
    return results


class OnMI(MessageBodyDataDict):
    """Message handler for ``onMI`` GOAT mower zone polygon messages.

    Assembles chunked LZMA payloads and fires :class:`MapSubsetEvent`
    events for each zone polygon, plus a :class:`MapChangedEvent` when
    the full batch is assembled.  Registers as handler for both ``onMI``
    (mowing zones) and ``onArI`` (sub-zone areas).
    """

    NAME = "onMI"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Accumulate chunks; fire events when batch is complete."""
        batid_raw: str = str(data.get("batid", ""))
        # Prefix with event_bus identity so concurrent devices don't share buffers
        batid: str = f"{id(event_bus)}:{batid_raw}" if batid_raw else ""
        serial: int = int(data.get("serial", 0))
        index: int = int(data.get("index", 0))
        mid: str = str(data.get("mid", "1"))
        info: str = str(data.get("info", ""))

        if not batid or not info or serial == 0:
            return HandlingResult.analyse()

        _cleanup_stale_batches()

        # Store raw chunk bytes
        try:
            raw = base64.b64decode(info)
        except Exception:
            _LOGGER.warning("onMI: base64 decode failed for batid=%s index=%d", batid, index)
            return HandlingResult.analyse()

        _chunk_buffer[batid][index] = raw
        _chunk_meta[batid] = {
            "total": serial,
            "timestamp": time.monotonic(),
        }

        _LOGGER.debug("onMI: chunk %d/%d received for batid=%s map=%s", index + 1, serial, batid, mid)

        if len(_chunk_buffer[batid]) < serial:
            return HandlingResult.success()  # waiting for more chunks

        # All chunks received — assemble and decompress
        try:
            all_raw = b"".join(_chunk_buffer[batid][i] for i in range(serial))
        except KeyError:
            _LOGGER.warning("onMI: missing chunk in batid=%s", batid)
            return HandlingResult.analyse()
        finally:
            _chunk_buffer.pop(batid, None)
            _chunk_meta.pop(batid, None)

        # Chunk 0: bytes 0-4 = LZMA1 filter props, bytes 5-8 = uint32 uncompressed len
        # Sanity-check header before allocating decompressor memory.
        try:
            if len(all_raw) < 9:
                msg = "payload too short for LZMA header"
                raise ValueError(msg)
            lzma_header = all_raw[0:5]
            uncompressed_len = struct.unpack("<I", all_raw[5:9])[0]
            compressed = all_raw[9:]
            if uncompressed_len > _MAX_UNCOMPRESSED_BYTES:
                msg = f"uncompressed_len {uncompressed_len} exceeds limit"
                raise ValueError(msg)
            # Decode LZMA1 filter properties from the 5-byte header without
            # relying on the private lzma._decode_filter_properties API.
            # Encoding: props_byte = (pb * 5 + lp) * 9 + lc  (LZMA spec §3.3)
            #   lc ∈ [0, 8], lp ∈ [0, 4], pb ∈ [0, 4]
            # Bytes 1-4: dictionary size as little-endian uint32
            props_byte = lzma_header[0]
            pb_lp, lc = divmod(props_byte, 9)   # 9 values for lc
            pb, lp = divmod(pb_lp, 5)            # 5 values for lp
            dict_size = struct.unpack("<I", lzma_header[1:5])[0]
            if dict_size > _MAX_DICT_SIZE_BYTES:
                msg = f"dict_size {dict_size} exceeds limit"
                raise ValueError(msg)
            filter_props = {
                "id": lzma.FILTER_LZMA1,
                "lc": lc,
                "lp": lp,
                "pb": pb,
                "dict_size": dict_size,
            }
            dec = lzma.LZMADecompressor(lzma.FORMAT_RAW, None, [filter_props])
            full_bytes = dec.decompress(compressed, uncompressed_len)
        except Exception as exc:
            _LOGGER.warning("onMI: decompression failed for batid=%s: %s", batid, exc)
            return HandlingResult.analyse()

        try:
            zones: list[Any] = orjson.loads(full_bytes)
        except Exception as exc:
            _LOGGER.warning("onMI: JSON parse failed for batid=%s: %s", batid, exc)
            return HandlingResult.analyse()

        _LOGGER.debug("onMI: decoded %d entries for map %s (batid=%s)", len(zones), mid, batid)

        # Collect all zone events first so we can emit MapSetEvent with full ID list
        zone_events: list[tuple[MapSetType, int, str]] = []
        for entry in zones:
            for type_code, zone_id_str, coords in _decode_entry(entry):
                try:
                    zone_id = int(zone_id_str)
                except (ValueError, TypeError):
                    _LOGGER.debug("onMI: skipping non-numeric zone id %r", zone_id_str)
                    continue
                if type_code == _ZONE_TYPE:
                    zone_events.append((MapSetType.ROOMS, zone_id, coords))
                elif type_code == _NO_GO_TYPE:
                    zone_events.append((MapSetType.NO_MOP_ZONES, zone_id, coords))

        # Emit MapSetEvent per type — use sorted unique IDs so MapRoomHandling's
        # len(event.subsets) count matches the number of unique MapSubsetEvents
        # we will emit (duplicates would inflate the count and block RoomsEvent).
        for set_type in (MapSetType.ROOMS, MapSetType.NO_MOP_ZONES):
            ids = sorted({ev[1] for ev in zone_events if ev[0] == set_type})
            if ids:
                event_bus.notify(MapSetEvent(type=set_type, subsets=ids, map_id=mid))

        # Now emit individual MapSubsetEvents
        for set_type, zone_id, coords in zone_events:
            event_bus.notify(
                MapSubsetEvent(
                    id=zone_id,
                    type=set_type,
                    # MapRoomHandling.on_map_subset gates on `not event.name`;
                    # a non-empty name is required for RoomsEvent to fire so that
                    # HA can enumerate zones for zone-mow commands.
                    name=str(zone_id) if set_type == MapSetType.ROOMS else None,
                    coordinates=coords,
                )
            )

        fired = len(zone_events)
        _LOGGER.debug("onMI: fired %d MapSubsetEvents for batid=%s", fired, batid)

        # Signal that the map has changed so image entities re-render
        event_bus.notify(MapChangedEvent(datetime.now(UTC)))

        # Satisfy request_refresh(CachedMapInfoEvent) callers: GetMI() is wired
        # as the cached_info getter so the library expects a CachedMapInfoEvent
        # after each getMI/onMI cycle.  The GOAT has no map-name/rotation metadata
        # so we emit an empty event (maps=set()); the Map class handles this safely.
        event_bus.notify(CachedMapInfoEvent(set()))

        return HandlingResult.success()


class OnArI(OnMI):
    """Handler for ``onArI`` sub-zone area messages.

    Uses the same chunked LZMA protocol as ``onMI`` and fires the same
    events.  Registered separately so both topic names are routed to the
    correct handler via the ``MESSAGES`` dict.
    """

    NAME = "onArI"
