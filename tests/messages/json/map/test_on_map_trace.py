"""Tests for OnMapTrace — mower variant with LZMA-compressed info field."""

from __future__ import annotations

import base64
from unittest.mock import Mock

import orjson
import pytest

from deebot_client.event_bus import EventBus
from deebot_client.events import FirmwareEvent
from deebot_client.events.map import (
    MapTraceEvent,
    MowerMapTraceEvent,
    MowerMapTraceGroup,
    MowerMapTraceSegment,
)
from deebot_client.message import HandlingState
from deebot_client.messages.json.map import OnMapTrace
from tests import get_static_device_info
from tests.messages.json import assert_message

# Static pre-encoded payloads (LZMA1 with trimmed header, base64).
# Generated from real GOAT A1600 RTK firmware 1.15.x encoding format.

# '[["7","0;100,200;150,250;"]]' (28 bytes uncompressed)
_SINGLE_GROUP = "XQAABAAcAAAAAC3ghG4jMKGNRtkww/d7MLX33z8usOwaHU2B7///wFIAAA=="

# '[["5","0;-11850,-28849;-11800,-28899;","0;-12850,-23699;-12800,-23750;"],["6","0;-7899,-39700;-7950,-39649;"]]' (110 bytes)
_MULTI_GROUP = "XQAABABuAAAAAC3ghGojMKGNRtiHVVsAoT/QJyYK0+w8iNNfkK1fJciMh2LrturUwS3TNs8H+7FN7dV1zViWeRKpxrkDUNNQG/4bayp4L33u+jJYgA=="

# '[]' (2 bytes)
_EMPTY_GROUPS = "XQAABAACAAAAAC2XXP/////wAAAA"

# '[["1","0;1,2;3,4;"]]' (20 bytes)
_SERIAL_TEST = "XQAABAAUAAAAAC3ghGIjMKGNR5N7rKaBA7QSJbYEb82/P//2SwAA"

# b'not json content' compressed — decompresses to non-JSON
_NON_JSON = "XQAABAAQAAAAADcbyuolm7SQrGkrEp4K2Iwi8deA//3qYAA="


@pytest.fixture(autouse=True)
def _clear_chunk_buffer() -> None:
    """Reset the class-level chunk reassembly buffer between tests.

    ``OnMapTrace`` keeps an in-flight buffer across dispatches so multi-
    chunk firmware payloads can be reassembled. Clear it between tests
    so they don't leak state into each other.
    """
    OnMapTrace._CHUNK_BUFFER.clear()


def _envelope(
    info_b64: str,
    info_size: int,
    *,
    fw: str = "1.15.13",
    index: str = "0",
    serial: str = "1",
    mid: str = "123456789",
    batid: str = "hmfald",
    type_: str = "4",
) -> dict:
    return {
        "header": {
            "pri": 1,
            "tzm": 120,
            "ts": "1777450352860644879",
            "fwVer": fw,
            "hwVer": "0.0.0",
        },
        "body": {
            "data": {
                "mid": mid,
                "batid": batid,
                "serial": serial,
                "index": index,
                "type": type_,
                "info": info_b64,
                "infoSize": info_size,
            }
        },
    }


def test_OnMapTrace_emits_structured_event_and_flat_compat() -> None:
    expected_groups = [
        MowerMapTraceGroup(
            group_id="7",
            segments=[
                MowerMapTraceSegment(
                    points=[(100, 200), (150, 250)],
                    raw="0;100,200;150,250;",
                ),
            ],
        )
    ]
    assert_message(
        OnMapTrace,
        _envelope(_SINGLE_GROUP, 28),
        (
            FirmwareEvent("1.15.13"),
            MowerMapTraceEvent(
                mid="123456789",
                batid="hmfald",
                serial="1",
                type="4",
                groups=expected_groups,
            ),
            MapTraceEvent(start=1, total=1, data="100,200;150,250"),
        ),
        device_class="xmp9ds",
    )


def test_OnMapTrace_preserves_groups_and_segments() -> None:
    expected_groups = [
        MowerMapTraceGroup(
            group_id="5",
            segments=[
                MowerMapTraceSegment(
                    points=[(-11850, -28849), (-11800, -28899)],
                    raw="0;-11850,-28849;-11800,-28899;",
                ),
                MowerMapTraceSegment(
                    points=[(-12850, -23699), (-12800, -23750)],
                    raw="0;-12850,-23699;-12800,-23750;",
                ),
            ],
        ),
        MowerMapTraceGroup(
            group_id="6",
            segments=[
                MowerMapTraceSegment(
                    points=[(-7899, -39700), (-7950, -39649)],
                    raw="0;-7899,-39700;-7950,-39649;",
                ),
            ],
        ),
    ]
    expected_flat = (
        "-11850,-28849;-11800,-28899;"
        "-12850,-23699;-12800,-23750;"
        "-7899,-39700;-7950,-39649"
    )
    assert_message(
        OnMapTrace,
        _envelope(_MULTI_GROUP, 110),
        (
            FirmwareEvent("1.15.13"),
            MowerMapTraceEvent(
                mid="123456789",
                batid="hmfald",
                serial="1",
                type="4",
                groups=expected_groups,
            ),
            MapTraceEvent(start=1, total=1, data=expected_flat),
        ),
        device_class="xmp9ds",
    )


def test_OnMapTrace_no_info_field_returns_analyse() -> None:
    envelope = _envelope("", 0)
    envelope["body"]["data"].pop("info")
    envelope["body"]["data"].pop("infoSize")
    assert_message(
        OnMapTrace,
        envelope,
        FirmwareEvent("1.15.13"),
        device_class="xmp9ds",
        expected_state=HandlingState.ANALYSE_LOGGED,
    )


def test_OnMapTrace_empty_groups_returns_analyse() -> None:
    assert_message(
        OnMapTrace,
        _envelope(_EMPTY_GROUPS, 2),
        FirmwareEvent("1.15.13"),
        device_class="xmp9ds",
        expected_state=HandlingState.ANALYSE_LOGGED,
    )


@pytest.mark.parametrize(
    ("broken_info", "info_size"),
    [
        ("@@@not-base64@@@", 100),  # base64 decode fails
        ("AQIDBA==", 0),  # missing infoSize → fall through
        (_NON_JSON, 16),  # decompresses, but result is not valid JSON
    ],
)
def test_OnMapTrace_corrupt_info_returns_analyse(
    broken_info: str, info_size: int
) -> None:
    assert_message(
        OnMapTrace,
        _envelope(broken_info, info_size),
        FirmwareEvent("1.15.13"),
        device_class="xmp9ds",
        expected_state=HandlingState.ANALYSE_LOGGED,
    )


def test_OnMapTrace_uses_constant_compat_start_not_serial() -> None:
    """Regression: ``serial`` is reused across batches in real captures.

    Per DeebotUniverse/client.py#1567 review, using ``serial`` as
    ``MapTraceEvent.start`` was incorrect. The compat event now uses a
    stable non-zero constant.
    """
    envelope = _envelope(_SERIAL_TEST, 20, serial="42")

    expected_groups = [
        MowerMapTraceGroup(
            group_id="1",
            segments=[
                MowerMapTraceSegment(points=[(1, 2), (3, 4)], raw="0;1,2;3,4;"),
            ],
        )
    ]
    assert_message(
        OnMapTrace,
        envelope,
        (
            FirmwareEvent("1.15.13"),
            MowerMapTraceEvent(
                mid="123456789",
                batid="hmfald",
                serial="42",
                type="4",
                groups=expected_groups,
            ),
            MapTraceEvent(start=1, total=1, data="1,2;3,4"),
        ),
        device_class="xmp9ds",
    )


# ---------------------------------------------------------------------------
# Chunk reassembly tests — payloads split across multiple ``index`` values
# ---------------------------------------------------------------------------


def _split_b64_into_chunks(b64: str, n: int) -> list[str]:
    """Split a base64-encoded payload into ``n`` raw-byte chunks.

    Each chunk is re-encoded as base64. Mirrors how the firmware
    paginates an LZMA stream across ``index`` values.
    """
    raw = base64.b64decode(b64)
    step = len(raw) // n
    chunks = [raw[i * step : (i + 1) * step] for i in range(n - 1)]
    chunks.append(raw[(n - 1) * step :])
    return [base64.b64encode(c).decode("ascii") for c in chunks]


def test_OnMapTrace_chunk_in_progress_emits_nothing_then_completes() -> None:
    """Multi-chunk LZMA stream: chunk 0 alone cannot be decompressed.

    Only when chunk 1 arrives does the buffer assemble and the events fire.
    """
    chunks = _split_b64_into_chunks(_MULTI_GROUP, 2)

    # First chunk — handler buffers, returns SUCCESS, emits no event.
    event_bus = Mock(spec_set=EventBus)
    static_device_info = get_static_device_info("xmp9ds")
    assert static_device_info is not None
    event_bus.capabilities = static_device_info.capabilities

    result_chunk0 = OnMapTrace.handle(event_bus, _envelope(chunks[0], 110, index="0"))
    assert result_chunk0.state == HandlingState.SUCCESS
    # FirmwareEvent fires on every dispatch — but no map events yet.
    assert event_bus.notify.call_count == 1
    notified_types = {type(c.args[0]).__name__ for c in event_bus.notify.call_args_list}
    assert "MowerMapTraceEvent" not in notified_types
    assert "MapTraceEvent" not in notified_types

    # Second chunk — buffer completes, structured + flat events emitted.
    result_chunk1 = OnMapTrace.handle(event_bus, _envelope(chunks[1], 110, index="1"))
    assert result_chunk1.state == HandlingState.SUCCESS
    notified_types = [type(c.args[0]).__name__ for c in event_bus.notify.call_args_list]
    assert "MowerMapTraceEvent" in notified_types
    assert "MapTraceEvent" in notified_types

    # Buffer cleared on completion.
    assert OnMapTrace._CHUNK_BUFFER == {}


def test_OnMapTrace_chunks_out_of_order_still_reassemble() -> None:
    """index=1 arriving before index=0 must still reassemble correctly.

    The buffer assembles in sorted order, not arrival order, so the LZMA
    decoder always sees the header bytes first once index=0 lands.
    """
    chunks = _split_b64_into_chunks(_MULTI_GROUP, 2)

    event_bus = Mock(spec_set=EventBus)
    static_device_info = get_static_device_info("xmp9ds")
    assert static_device_info is not None
    event_bus.capabilities = static_device_info.capabilities

    # index=1 first — handler buffers but can't decompress (no header yet).
    OnMapTrace.handle(event_bus, _envelope(chunks[1], 110, index="1"))
    notified_types = [type(c.args[0]).__name__ for c in event_bus.notify.call_args_list]
    assert "MowerMapTraceEvent" not in notified_types

    # index=0 second — now the contiguous prefix exists, assembly succeeds.
    OnMapTrace.handle(event_bus, _envelope(chunks[0], 110, index="0"))
    notified_types = [type(c.args[0]).__name__ for c in event_bus.notify.call_args_list]
    assert "MowerMapTraceEvent" in notified_types


def test_OnMapTrace_new_cycle_drops_partial_previous_buffer() -> None:
    """A second index=0 for the same key resets that key's buffer.

    This handles the firmware retrying a cycle (e.g. after an MQTT
    disconnect) without piling up partial chunks forever.
    """
    chunks = _split_b64_into_chunks(_MULTI_GROUP, 2)

    event_bus = Mock(spec_set=EventBus)
    static_device_info = get_static_device_info("xmp9ds")
    assert static_device_info is not None
    event_bus.capabilities = static_device_info.capabilities

    # First attempt: only chunk 0 — buffered, no decompression yet.
    OnMapTrace.handle(event_bus, _envelope(chunks[0], 110, index="0"))
    key = ("123456789", "hmfald", "1", "4")
    assert key in OnMapTrace._CHUNK_BUFFER
    assert list(OnMapTrace._CHUNK_BUFFER[key].keys()) == [0]

    # Same key, fresh index=0 → previous partial buffer replaced.
    # Use the FULL single-group payload here so this fresh cycle
    # completes in one go.
    OnMapTrace.handle(event_bus, _envelope(_SINGLE_GROUP, 28, index="0"))
    # The buffer was reset on the second index=0 arrival, then completed
    # and popped on assembly. Either way it must not still hold the
    # original partial slice from chunk 0 of _MULTI_GROUP.
    assert key not in OnMapTrace._CHUNK_BUFFER


def test_OnMapTrace_different_keys_have_independent_buffers() -> None:
    """Concurrent mowing cycles must not stomp on each other's state.

    Different ``serial`` or ``batid`` values produce independent buffer keys.
    """
    chunks = _split_b64_into_chunks(_MULTI_GROUP, 2)

    event_bus = Mock(spec_set=EventBus)
    static_device_info = get_static_device_info("xmp9ds")
    assert static_device_info is not None
    event_bus.capabilities = static_device_info.capabilities

    OnMapTrace.handle(event_bus, _envelope(chunks[0], 110, index="0", serial="1"))
    OnMapTrace.handle(event_bus, _envelope(chunks[0], 110, index="0", serial="2"))

    assert ("123456789", "hmfald", "1", "4") in OnMapTrace._CHUNK_BUFFER
    assert ("123456789", "hmfald", "2", "4") in OnMapTrace._CHUNK_BUFFER

    # Completing one key does not affect the other.
    OnMapTrace.handle(event_bus, _envelope(chunks[1], 110, index="1", serial="1"))
    assert ("123456789", "hmfald", "1", "4") not in OnMapTrace._CHUNK_BUFFER
    assert ("123456789", "hmfald", "2", "4") in OnMapTrace._CHUNK_BUFFER


def test_OnMapTrace_parse_groups_handles_malformed_input() -> None:
    """_parse_groups skips non-list groups, non-string segments, malformed points.

    Covers the individual guard branches inside the parser that a corrupt
    firmware payload can trip (Codecov: 87% patch → aims for the missing
    per-item branches).
    """
    # non-JSON list → returns None
    assert OnMapTrace._parse_groups(b'{"not":"a list"}') is None

    # invalid JSON → returns None
    assert OnMapTrace._parse_groups(b"not json at all") is None

    # empty list at top level → returns empty group list (not None)
    assert OnMapTrace._parse_groups(b"[]") == []

    # Mix of malformed and one good group
    payload = orjson.dumps(
        [
            "not-a-list-group",  # non-list group → skipped
            [],  # empty group (no id) → skipped
            ["7", 12345, None],  # non-string segments → skipped
            [
                "8",
                "not-a-point;bad,coord;",
                "0;1,2;bad,notanint;3,4;",
            ],
        ]
    )
    groups = OnMapTrace._parse_groups(payload)
    # Only group "8" survives, and only its valid points make it in.
    assert groups is not None
    assert len(groups) == 1
    assert groups[0].group_id == "8"
    # The first segment yields no valid coordinate pairs → skipped
    # (a segment that yields zero points is dropped by the parser).
    # The second segment gives (1,2) and (3,4); "bad,notanint" is skipped.
    assert len(groups[0].segments) == 1
    assert groups[0].segments[0].points == [(1, 2), (3, 4)]


def test_OnMapTrace_evict_to_make_room_drops_oldest_by_total_bytes() -> None:
    """When the accumulated buffer would exceed the global cap, oldest keys drop.

    Covers the ``while _total() + incoming > _MAX_TOTAL_BYTES`` branch of
    ``_evict_to_make_room`` that per-key eviction alone doesn't exercise.
    """
    # Fill the buffer just under the total cap with a few keys, then request
    # room for a chunk large enough to push over the limit.
    payload = b"\x00" * 500_000  # 500 kB
    OnMapTrace._CHUNK_BUFFER[("mid", "batid", "1", "4")] = {0: payload}
    OnMapTrace._CHUNK_BUFFER[("mid", "batid", "2", "4")] = {0: payload}
    OnMapTrace._CHUNK_BUFFER[("mid", "batid", "3", "4")] = {0: payload}
    # Total buffered = 1.5 MB. Adding 700 kB would push above 2 MB cap.
    OnMapTrace._evict_to_make_room(700_000)
    # At least one key was evicted to fit the incoming payload under the cap.
    remaining_total = sum(
        len(b) for chunks in OnMapTrace._CHUNK_BUFFER.values() for b in chunks.values()
    )
    assert remaining_total + 700_000 <= OnMapTrace._MAX_TOTAL_BYTES


def test_OnMapTrace_evict_to_make_room_caps_keys_tracked() -> None:
    """Adding more than _MAX_KEYS_TRACKED cycles drops the oldest one first."""
    # Fill exactly at the limit with tiny chunks (won't trigger byte-cap eviction)
    tiny = b"\x00" * 10
    for i in range(OnMapTrace._MAX_KEYS_TRACKED):
        OnMapTrace._CHUNK_BUFFER[("mid", "batid", str(i), "4")] = {0: tiny}
    assert len(OnMapTrace._CHUNK_BUFFER) == OnMapTrace._MAX_KEYS_TRACKED

    # Request room for a tiny incoming — should evict the oldest key.
    OnMapTrace._evict_to_make_room(10)
    assert len(OnMapTrace._CHUNK_BUFFER) < OnMapTrace._MAX_KEYS_TRACKED


def test_OnMapTrace_per_key_byte_cap_drops_runaway_buffer() -> None:
    """Firmware misbehaving must not pin memory.

    When the per-key buffer would exceed the cap (final chunk never arrives),
    drop it instead of growing forever.
    """
    # Stuff a chunk just under the cap, then push another that would
    # cross it. The second push must drop the buffer.
    fake_chunk = base64.b64encode(b"\x00" * 100_000).decode("ascii")
    big_chunk = base64.b64encode(b"\x00" * 500_000).decode("ascii")

    event_bus = Mock(spec_set=EventBus)
    static_device_info = get_static_device_info("xmp9ds")
    assert static_device_info is not None
    event_bus.capabilities = static_device_info.capabilities

    result1 = OnMapTrace.handle(event_bus, _envelope(fake_chunk, 999_999, index="0"))
    assert result1.state == HandlingState.SUCCESS
    key = ("123456789", "hmfald", "1", "4")
    assert key in OnMapTrace._CHUNK_BUFFER

    # Crossing the per-key cap → buffer dropped, dispatched as ANALYSE.
    result2 = OnMapTrace.handle(event_bus, _envelope(big_chunk, 999_999, index="1"))
    assert result2.state == HandlingState.ANALYSE_LOGGED
    assert key not in OnMapTrace._CHUNK_BUFFER
