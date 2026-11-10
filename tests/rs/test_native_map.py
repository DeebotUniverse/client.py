"""Synthetic tests for native raw-LZ4 raster and trace Rust bridge."""

from __future__ import annotations

import base64

import pytest

from deebot_client.events.map import MapSetType, MapSubsetEvent, Position
from deebot_client.rs.map import (
    BackgroundImage,
    MapData,
    PositionType,
    RotationAngle,
    TracePoints,
)


def _compress_raw_lz4(data: bytes) -> str:
    n = len(data)
    out = bytearray()
    if n >= 15:
        token = 15 << 4
        out.append(token)
        extra = n - 15
        while extra >= 255:
            out.append(255)
            extra -= 255
        out.append(extra)
    else:
        token = n << 4
        out.append(token)
    out.extend(data)
    return base64.b64encode(bytes(out)).decode("ascii")


def _encode_trace_chunk(records: list[tuple[int, int, int]]) -> tuple[str, int]:
    raw = bytearray()
    for x, y, flag in records:
        raw.extend(int(x).to_bytes(2, byteorder="little", signed=True))
        raw.extend(int(y).to_bytes(2, byteorder="little", signed=True))
        raw.append(int(flag) & 0xFF)
    b64 = _compress_raw_lz4(bytes(raw))
    return b64, len(raw)


def test_native_raster_asymmetric_render() -> None:
    # Synthetic 5x3 asymmetric grid
    # Row 0: wall (0xff), floor (0x00), floor (0x00), floor (0x00), room 1 (0x01)
    # Row 1: floor (0x00), floor (0x00), floor (0x00), floor (0x00), floor (0x00)
    # Row 2: room 2 (0x02), floor (0x00), floor (0x00), floor (0x00), room 3 (0x03)
    raw = bytes(
        [
            0xFF,
            0x00,
            0x00,
            0x00,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x02,
            0x00,
            0x00,
            0x00,
            0x03,
        ]
    )
    b64_lz4 = _compress_raw_lz4(raw)

    md = MapData()
    bg = md.background_image

    # First update: changes state -> True
    updated = bg.set_native_raster(
        base64_lz4=b64_lz4,
        width=5,
        height=3,
        x_min=120,
        y_max=230,
        resolution=5,
    )
    assert updated is True

    # Identical update: no change -> False
    updated_again = bg.set_native_raster(
        base64_lz4=b64_lz4,
        width=5,
        height=3,
        x_min=120,
        y_max=230,
        resolution=5,
    )
    assert updated_again is False

    svg = md.generate_svg([], [], RotationAngle.DEG_0)
    assert svg is not None
    assert "image-rendering: pixelated" in svg
    assert 'x="-280"' in svg
    assert 'y="-172"' in svg
    assert 'width="5"' in svg
    assert 'height="3"' in svg
    assert 'viewBox="-292 -184 29 27"' in svg


def test_native_raster_dimension_bounds_fail() -> None:
    bg = BackgroundImage()
    raw = bytes([0x00] * 10)
    b64 = _compress_raw_lz4(raw)

    with pytest.raises(ValueError, match="dimensions must be > 0"):
        bg.set_native_raster(b64, 0, 10, 120, 230, 5)

    with pytest.raises(ValueError, match="dimensions must be > 0"):
        bg.set_native_raster(b64, 10, 0, 120, 230, 5)

    with pytest.raises(ValueError, match="exceed maximum"):
        bg.set_native_raster(b64, 801, 10, 120, 230, 5)

    with pytest.raises(ValueError, match="Resolution must be > 0"):
        bg.set_native_raster(b64, 5, 2, 120, 230, 0)


def test_native_raster_unsupported_resolution_fail() -> None:
    bg = BackgroundImage()
    raw = bytes([0x00] * 4)
    b64 = _compress_raw_lz4(raw)

    with pytest.raises(ValueError, match="Unsupported resolution"):
        bg.set_native_raster(b64, 2, 2, 120, 230, 10)

    with pytest.raises(ValueError, match="Unsupported resolution"):
        bg.set_native_raster(b64, 2, 2, 120, 230, 1)


def test_native_raster_extreme_extents_fail_without_panic() -> None:
    bg = BackgroundImage()
    raw = bytes([0x00] * 4)
    b64 = _compress_raw_lz4(raw)

    with pytest.raises(ValueError, match="extents overflow"):
        bg.set_native_raster(b64, 2, 2, -32768, 230, 5)

    with pytest.raises(ValueError, match="extents overflow"):
        bg.set_native_raster(b64, 2, 2, 0, -32768, 5)

    with pytest.raises(ValueError, match="extents overflow"):
        bg.set_native_raster(b64, 800, 800, 32767, 230, 5)

    # Negative but valid extents still render
    md = MapData()
    assert md.background_image.set_native_raster(b64, 2, 2, -1000, 500, 5) is True
    svg = md.generate_svg([], [], RotationAngle.DEG_0)
    assert svg is not None
    assert 'viewBox="-1412 87 26 26"' in svg


def test_native_raster_malformed_inputs_fail_without_mutation() -> None:
    md = MapData()
    bg = md.background_image

    valid_raw = bytes([0x00] * 6)
    valid_b64 = _compress_raw_lz4(valid_raw)
    assert bg.set_native_raster(valid_b64, 3, 2, 400, 400, 5) is True

    # Truncated base64
    with pytest.raises(ValueError, match="Base64"):
        bg.set_native_raster("invalid-base64-!@#$", 3, 2, 400, 400, 5)

    # Size mismatch: payload decompresses to 6 bytes but requested 10
    with pytest.raises(ValueError, match="size mismatch"):
        bg.set_native_raster(valid_b64, 5, 2, 400, 400, 5)

    # State still intact after failures
    svg = md.generate_svg([], [], RotationAngle.DEG_0)
    assert svg is not None
    assert 'width="3"' in svg
    assert 'height="2"' in svg


def test_trace_points_basic_and_flags() -> None:
    tp = TracePoints()
    # P0: flag 154 (bit 7 = 1 -> disconnected)
    # P1: flag 0 (bit 7 = 0 -> connected)
    records = [(100, -200, 154), (105, -195, 0)]
    b64, raw_len = _encode_trace_chunk(records)

    updated = tp.set_native(b64, raw_len + 16, 0, 3)
    assert updated is True

    # Retransmission without changes -> False
    updated_dup = tp.set_native(b64, raw_len + 16, 0, 3)
    assert updated_dup is False


def test_trace_points_cursor_overlap_and_reset() -> None:
    md = MapData()
    tp = md.trace_points

    # Initial packet: start=0, points [P0, P1]
    rec1 = [(0, 0, 128), (5, 5, 0)]
    b64_1, len1 = _encode_trace_chunk(rec1)
    assert tp.set_native(b64_1, len1 + 16, 0, 3) is True

    # Overlap packet: start=1, points [P1, P2]
    rec2 = [(5, 5, 0), (10, 10, 0)]
    b64_2, len2 = _encode_trace_chunk(rec2)
    assert tp.set_native(b64_2, len2 + 16, 1, 4) is True

    # Reset with start=0
    rec3 = [(20, 20, 128)]
    b64_3, len3 = _encode_trace_chunk(rec3)
    assert tp.set_native(b64_3, len3 + 16, 0, 2) is True


def test_trace_points_gap_and_bounds_validation() -> None:
    tp = TracePoints()
    rec = [(0, 0, 0)]
    b64, raw_len = _encode_trace_chunk(rec)

    # Initial point
    assert tp.set_native(b64, raw_len + 16, 0, 2) is True

    # Gap: current count is 1, incoming start is 4 -> missing points 1..3
    with pytest.raises(ValueError, match="Trace cursor gap"):
        tp.set_native(b64, raw_len + 16, 4, 6)

    # start > total -> invalid
    with pytest.raises(ValueError, match=r"start .* > total"):
        tp.set_native(b64, raw_len + 16, 5, 2)

    # capacity > 640000 -> exceeded
    with pytest.raises(ValueError, match=r"capacity .* exceeds maximum"):
        tp.set_native(b64, 700_000, 1, 3)


def test_trace_points_empty_reset_and_clear() -> None:
    tp = TracePoints()
    rec = [(10, 10, 0)]
    b64, raw_len = _encode_trace_chunk(rec)
    assert tp.set_native(b64, raw_len + 16, 0, 2) is True

    # Empty payload with start=0, total=0 clears buffer
    assert tp.set_native(None, 0, 0, 0) is True
    # Calling again when already empty -> False
    assert tp.set_native(None, 0, 0, 0) is False

    # Clear method
    assert tp.set_native(b64, raw_len + 16, 0, 2) is True
    tp.clear()
    assert tp.set_native(None, 0, 0, 0) is False


def test_combined_native_map_svg() -> None:
    md = MapData()
    bg = md.background_image
    tp = md.trace_points

    # Raster
    raw = bytes([0x00] * 25)
    b64_lz4 = _compress_raw_lz4(raw)
    assert bg.set_native_raster(b64_lz4, 5, 5, 398, 402, 5) is True

    # Trace
    rec = [(0, 0, 128), (5, 5, 0), (10, 5, 0)]
    b64_tr, len_tr = _encode_trace_chunk(rec)
    assert tp.set_native(b64_tr, len_tr + 16, 0, 4) is True

    positions = [
        Position(PositionType.DEEBOT, 5000, -5000, 0),
        Position(PositionType.CHARGER, 0, 0, 180),
    ]
    subsets = [
        MapSubsetEvent(1, MapSetType.VIRTUAL_WALLS, "[-100,100,100,100]"),
    ]

    svg = md.generate_svg(subsets, positions, RotationAngle.DEG_0)
    assert svg is not None
    assert "image-rendering: pixelated" in svg
    assert 'transform="scale(0.2-0.2)"' in svg
    assert 'href="#d"' in svg
    assert 'href="#c"' in svg
    assert 'class="v"' in svg


def test_trace_points_total_ceiling_fail() -> None:
    tp = TracePoints()
    rec = [(0, 0, 0)]
    b64, raw_len = _encode_trace_chunk(rec)

    with pytest.raises(ValueError, match=r"total .* exceeds maximum"):
        tp.set_native(b64, raw_len + 16, 0, 128001)


def test_trace_points_chunk_exceeding_total_fail() -> None:
    tp = TracePoints()
    rec3 = [(0, 0, 0), (1, 1, 0), (2, 2, 0)]
    b64_3, len_3 = _encode_trace_chunk(rec3)

    with pytest.raises(ValueError, match=r"chunk .* exceeds declared total"):
        tp.set_native(b64_3, len_3 + 16, 0, 2)

    # Generic bound valid: 2 points with total 2, no total-start-1 theory
    rec2 = [(10, -5, 154), (11, -4, 0)]
    b64_2, len_2 = _encode_trace_chunk(rec2)
    assert tp.set_native(b64_2, len_2 + 16, 0, 2) is True


def test_trace_points_failed_chunk_preserves_prior() -> None:
    tp = TracePoints()
    rec = [(7, 8, 128), (9, 10, 0)]
    b64, raw_len = _encode_trace_chunk(rec)
    assert tp.set_native(b64, raw_len + 16, 0, 2) is True

    with pytest.raises(ValueError, match="Base64 decode failed"):
        tp.set_native("!!!not-base64!!!", 100, 2, 4)

    # Prior trace intact: identical retransmission reports no change
    assert tp.set_native(b64, raw_len + 16, 0, 2) is False


def test_native_raster_compressed_too_large_fail() -> None:
    bg = BackgroundImage()
    deterministic = bytes([0xAA] * 644_000)
    b64 = base64.b64encode(deterministic).decode("ascii")
    assert len(b64) <= 860_000
    with pytest.raises(ValueError, match=r"LZ4 payload length .* exceeds maximum"):
        bg.set_native_raster(b64, 800, 800, 0, 800, 5)
