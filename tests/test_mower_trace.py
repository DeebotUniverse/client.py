"""Tests for the MowerMapTrace accumulator and SVG renderer."""

from __future__ import annotations

import pytest

from deebot_client.events.map import MowerMapTraceGroup, MowerMapTraceSegment
from deebot_client.mower_trace import MowerMapTrace


def test_empty_trace_renders_to_none() -> None:
    trace = MowerMapTrace()
    assert not trace.has_points
    assert trace.to_svg() is None


def test_add_data_parses_tokens_and_returns_count() -> None:
    trace = MowerMapTrace()
    added = trace.add_data("0,0;100,200;300,400")
    assert added == 3
    assert trace.has_points


def test_add_data_skips_malformed_tokens() -> None:
    trace = MowerMapTrace()
    added = trace.add_data("0,0;not-a-point;100,abc;200,300;;")
    # Only "0,0" and "200,300" parse cleanly.
    assert added == 2


def test_add_data_returns_zero_on_all_invalid() -> None:
    trace = MowerMapTrace()
    assert trace.add_data(";;not-valid;") == 0
    assert not trace.has_points


def test_clear_drops_all_points() -> None:
    trace = MowerMapTrace()
    trace.add_data("1,2;3,4")
    trace.clear()
    assert not trace.has_points
    assert trace.to_svg() is None


def test_max_points_fifo_drop() -> None:
    trace = MowerMapTrace()
    over = MowerMapTrace.MAX_POINTS + 100
    payload = ";".join(f"{i},{i}" for i in range(over))
    added = trace.add_data(payload)
    assert added == over

    svg = trace.to_svg()
    assert svg is not None

    # Polyline holds exactly MAX_POINTS coordinate pairs after FIFO drop.
    points_attr = svg.split('points="', 1)[1].split('"', 1)[0]
    assert len(points_attr.split(" ")) == MowerMapTrace.MAX_POINTS

    # The MAX_POINTS most recent points are kept; first kept point has
    # x = (over - MAX_POINTS), here 100.
    first_kept_x = over - MowerMapTrace.MAX_POINTS
    assert points_attr.startswith(f"{first_kept_x},")


@pytest.mark.parametrize(
    ("raw", "expected_substrings", "absent_substrings"),
    [
        # Single-point trace: padding gives a non-zero viewBox.
        ("500,500", ["polyline", "viewBox=", "stroke="], []),
        # Two-point trace: SVG contains the flipped polyline points.
        ("0,0;100,100", ["polyline points=", "viewBox="], []),
    ],
)
def test_to_svg_structure(
    raw: str, expected_substrings: list[str], absent_substrings: list[str]
) -> None:
    trace = MowerMapTrace()
    trace.add_data(raw)
    svg = trace.to_svg()
    assert svg is not None
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    for needle in expected_substrings:
        assert needle in svg
    for needle in absent_substrings:
        assert needle not in svg


def test_add_groups_flattens_structured_payload() -> None:
    trace = MowerMapTrace()
    groups = [
        MowerMapTraceGroup(
            group_id="5",
            segments=[
                MowerMapTraceSegment(points=[(0, 0), (10, 20)]),
                MowerMapTraceSegment(points=[(100, 100)]),
            ],
        ),
        MowerMapTraceGroup(
            group_id="6",
            segments=[MowerMapTraceSegment(points=[(200, 200)])],
        ),
    ]
    added = trace.add_groups(groups)
    assert added == 4
    assert trace.has_points
    svg = trace.to_svg()
    assert svg is not None


def test_add_groups_empty_input_returns_zero() -> None:
    trace = MowerMapTrace()
    assert trace.add_groups([]) == 0
    assert not trace.has_points


def test_add_groups_groups_without_segments_yield_no_points() -> None:
    trace = MowerMapTrace()
    groups = [MowerMapTraceGroup(group_id="9", segments=[])]
    assert trace.add_groups(groups) == 0
    assert not trace.has_points


def test_to_svg_y_axis_is_flipped() -> None:
    """SVG renders top-down; mower coords are bottom-up. Verify the flip."""
    trace = MowerMapTrace()
    trace.add_data("0,0;0,1000")
    svg = trace.to_svg()
    assert svg is not None
    # Extract the polyline points attribute.
    points = svg.split('points="', 1)[1].split('"', 1)[0].split(" ")
    # Two points, both with x=0; y values must be swapped versus input
    # (input 0 -> output max_y+min_y-0 = larger value;
    #  input 1000 -> output max_y+min_y-1000 = smaller value).
    y0 = int(points[0].split(",")[1])
    y1 = int(points[1].split(",")[1])
    assert y0 > y1
