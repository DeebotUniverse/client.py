"""Tests for OnMI / OnArI GOAT mower zone-map message handlers."""

from __future__ import annotations

import base64
import lzma
import struct
from typing import Any
from unittest.mock import Mock

import orjson
import pytest

from deebot_client.event_bus import EventBus
from deebot_client.events.map import (
    CachedMapInfoEvent,
    MapChangedEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
)
from deebot_client.message import HandlingState
from deebot_client.messages.json.mow import OnArI, OnMI


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_lzma_payload(zones: list[Any]) -> str:
    """Return base64 of a single-chunk onMI payload for the given zone list."""
    raw = orjson.dumps(zones)
    filters = [{"id": lzma.FILTER_LZMA1, "preset": 6}]
    compressed = lzma.compress(raw, format=lzma.FORMAT_RAW, filters=filters)
    # First 5 bytes of ALONE format are the filter-property header
    alone = lzma.compress(raw, format=lzma.FORMAT_ALONE, filters=filters)
    props = alone[0:5]
    payload = props + struct.pack("<I", len(raw)) + compressed
    return base64.b64encode(payload).decode()


def _make_message(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "header": {"tzm": -420, "ts": "1781463003383", "fwVer": "1.13.31"},
        "body": {"data": data},
    }


def _notified(mock: Mock) -> list[Any]:
    """Return list of all objects passed to mock.notify()."""
    return [c.args[0] for c in mock.notify.call_args_list]


# Two mowing zones (type=1) + one no-go (type=4)
_ZONES = [
    [1, "0,100,200;300,200;300,400;100,400"],
    [1, "1,500,100;700,100;700,300;500,300"],
    [4, "2,50,50;150,50;150,150;50,150"],
]
_CHUNK_B64 = _make_lzma_payload(_ZONES)


# ---------------------------------------------------------------------------
# Single-chunk happy path
# ---------------------------------------------------------------------------

@pytest.mark.benchmark
def test_onMI_single_chunk_fires_events() -> None:
    """serial=1 batch: should emit MapSetEvent, MapSubsetEvents, MapChangedEvent."""
    event_bus = Mock(spec_set=EventBus)

    result = OnMI.handle(
        event_bus,
        _make_message({"batid": "sc-1", "serial": 1, "index": 0, "mid": "42", "info": _CHUNK_B64}),
    )
    assert result.state == HandlingState.SUCCESS

    notified = _notified(event_bus)

    # Two MapSetEvents (one per type present in the batch)
    assert MapSetEvent(type=MapSetType.ROOMS, subsets=[0, 1], map_id="42") in notified
    assert MapSetEvent(type=MapSetType.NO_MOP_ZONES, subsets=[2], map_id="42") in notified

    # MapSubsetEvents — name is str(id) for ROOMS, None for NO_MOP_ZONES
    assert MapSubsetEvent(
        id=0, type=MapSetType.ROOMS, name="0", coordinates="100,200;300,200;300,400;100,400"
    ) in notified
    assert MapSubsetEvent(
        id=1, type=MapSetType.ROOMS, name="1", coordinates="500,100;700,100;700,300;500,300"
    ) in notified
    assert MapSubsetEvent(
        id=2, type=MapSetType.NO_MOP_ZONES, name=None, coordinates="50,50;150,50;150,150;50,150"
    ) in notified

    # MapChangedEvent is fired with a live datetime; just assert type
    assert any(isinstance(n, MapChangedEvent) for n in notified)

    # CachedMapInfoEvent is emitted at end of batch so request_refresh callers unblock
    assert CachedMapInfoEvent(set()) in notified

    # Exactly: 2 MapSetEvents + 3 MapSubsetEvents + 1 MapChangedEvent + 1 CachedMapInfoEvent
    assert event_bus.notify.call_count == 7


# ---------------------------------------------------------------------------
# Multi-chunk reassembly — same event_bus to preserve batid prefix
# ---------------------------------------------------------------------------

@pytest.mark.benchmark
def test_onMI_multi_chunk_out_of_order_reassembly() -> None:
    """Chunks delivered out of order reassemble correctly when serial=2."""
    zones = [[1, "0,10,20;30,20"]]
    raw = orjson.dumps(zones)
    filters = [{"id": lzma.FILTER_LZMA1, "preset": 6}]
    compressed = lzma.compress(raw, format=lzma.FORMAT_RAW, filters=filters)
    alone = lzma.compress(raw, format=lzma.FORMAT_ALONE, filters=filters)
    props = alone[0:5]
    full = props + struct.pack("<I", len(raw)) + compressed

    mid_point = len(full) // 2
    chunk0 = base64.b64encode(full[:mid_point]).decode()
    chunk1 = base64.b64encode(full[mid_point:]).decode()

    # Same mock used for both calls so batid prefix (id(event_bus)) is identical
    event_bus = Mock(spec_set=EventBus)
    batid = "mc-reassembly"

    # Deliver chunk index=1 first — incomplete batch, no notifications
    r1 = OnMI.handle(
        event_bus,
        _make_message({"batid": batid, "serial": 2, "index": 1, "mid": "1", "info": chunk1}),
    )
    assert r1.state == HandlingState.SUCCESS
    event_bus.notify.assert_not_called()

    # Deliver chunk index=0 — batch complete, events fire
    r2 = OnMI.handle(
        event_bus,
        _make_message({"batid": batid, "serial": 2, "index": 0, "mid": "1", "info": chunk0}),
    )
    assert r2.state == HandlingState.SUCCESS

    notified = _notified(event_bus)
    assert MapSetEvent(type=MapSetType.ROOMS, subsets=[0], map_id="1") in notified
    assert MapSubsetEvent(
        id=0, type=MapSetType.ROOMS, name="0", coordinates="10,20;30,20"
    ) in notified
    assert any(isinstance(n, MapChangedEvent) for n in notified)
    assert CachedMapInfoEvent(set()) in notified


# ---------------------------------------------------------------------------
# Malformed / invalid payloads — must not crash
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "override",
    [
        {"batid": "", "serial": 1, "index": 0, "mid": "1", "info": _CHUNK_B64},
        {"batid": "x", "serial": 0, "index": 0, "mid": "1", "info": _CHUNK_B64},
        {"batid": "x", "serial": 1, "index": 0, "mid": "1", "info": "!!!not-b64!!!"},
        # bad-lzma: valid 9-byte header (props + small dict + small uncompressed_len)
        # but the compressed bytes are garbage, so LZMADecompressor raises LZMAError
        {
            "batid": "x",
            "serial": 1,
            "index": 0,
            "mid": "1",
            "info": base64.b64encode(
                # props=0x5d (lc=3,lp=0,pb=2) + dict_size=64KB + unclen=100 + garbage
                b"\x5d\x00\x00\x01\x00" + struct.pack("<I", 100) + b"not_valid_lzma"
            ).decode(),
        },
        # too short — raw bytes < 9 so header fields can't be read
        {
            "batid": "x",
            "serial": 1,
            "index": 0,
            "mid": "1",
            "info": base64.b64encode(b"short").decode(),
        },
        # oversized uncompressed_len — uint32 value = 0xFFFFFFFF (> 4 MB limit)
        {
            "batid": "x",
            "serial": 1,
            "index": 0,
            "mid": "1",
            "info": base64.b64encode(
                b"\x5d" + b"\x00" * 4 + b"\xff\xff\xff\xff"
            ).decode(),
        },
    ],
    ids=["empty-batid", "serial-zero", "bad-b64", "bad-lzma", "too-short", "huge-uncompressed"],
)
@pytest.mark.benchmark
def test_onMI_malformed_returns_analyse(override: dict[str, Any]) -> None:
    event_bus = Mock(spec_set=EventBus)
    result = OnMI.handle(event_bus, _make_message(override))
    assert result.state == HandlingState.ANALYSE
    event_bus.notify.assert_not_called()


# ---------------------------------------------------------------------------
# OnArI is a separate handler with a distinct NAME but identical behaviour
# ---------------------------------------------------------------------------

def test_onArI_and_onMI_names_are_distinct() -> None:
    assert OnArI.NAME == "onArI"
    assert OnMI.NAME == "onMI"
    assert OnArI.NAME != OnMI.NAME
