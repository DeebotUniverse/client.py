"""Test rust map module."""

from __future__ import annotations

import pytest

from deebot_client.rs.map import MapData


@pytest.mark.parametrize(
    ("value", "expected_error"),
    [
        ("invalid_base64", "Invalid symbol 95, offset 7.;value:invalid_base64"),
        ("", "Invalid 7z compressed data;value:"),
    ],
)
def test_MapData_add_trace_points_invalid(value: str, expected_error: str) -> None:
    """Test invalid MapData.add_trace_points."""
    map_data = MapData()
    with pytest.raises(ValueError, match=expected_error):
        map_data.add_trace_points(value)


@pytest.mark.parametrize(
    ("index", "base64_data", "expected_error"),
    [
        (
            10000,
            "invalid_base64",
            "Index out of bounds;index:10000,base64_data:invalid_base64",
        ),
        (
            1,
            "invalid_base64",
            "Invalid symbol 95, offset 7.;index:1,base64_data:invalid_base64",
        ),
        (1, "", "Invalid 7z compressed data;index:1,base64_data:"),
    ],
)
def test_MapData_update_map_piece_invalid(
    index: int, base64_data: str, expected_error: str
) -> None:
    """Test invalid MapData.update_map_piece."""
    map_data = MapData()
    with pytest.raises(ValueError, match=expected_error):
        map_data.update_map_piece(index, base64_data)
