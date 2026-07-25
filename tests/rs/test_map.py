"""Test rust map module."""

from __future__ import annotations

import math

import pytest
from testfixtures import LogCapture

from deebot_client.rs.map import (
    MapData,
    PositionType,
    RotationAngle,
    svg_point_to_device,
    svg_rectangle_to_custom_area,
)


@pytest.mark.parametrize(
    ("rotation", "expected"),
    [
        (RotationAngle.DEG_0, (63, 125)),
        (RotationAngle.DEG_90, (-125, 63)),
        (RotationAngle.DEG_180, (-63, -125)),
        (RotationAngle.DEG_270, (125, -63)),
    ],
)
def test_svg_point_to_device(
    rotation: RotationAngle, expected: tuple[int, int]
) -> None:
    assert svg_point_to_device((1.25, -2.5), rotation) == expected


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ((20.0, -40.0), (60.0, 10.0)),
        ((60.0, 10.0), (20.0, -40.0)),
        ((20.0, 10.0), (60.0, -40.0)),
        ((60.0, -40.0), (20.0, 10.0)),
    ],
)
def test_svg_rectangle_to_custom_area_drag_direction(
    start: tuple[float, float], end: tuple[float, float]
) -> None:
    assert svg_rectangle_to_custom_area(start, end, RotationAngle.DEG_0) == [
        1000,
        2000,
        3000,
        -500,
    ]


@pytest.mark.parametrize(
    ("start", "end", "rotation"),
    [
        ((20.0, -40.0), (60.0, 10.0), RotationAngle.DEG_0),
        ((40.0, 20.0), (-10.0, 60.0), RotationAngle.DEG_90),
        ((-20.0, 40.0), (-60.0, -10.0), RotationAngle.DEG_180),
        ((-40.0, -20.0), (10.0, -60.0), RotationAngle.DEG_270),
    ],
)
def test_svg_rectangle_to_custom_area_equivalent_rotations(
    start: tuple[float, float],
    end: tuple[float, float],
    rotation: RotationAngle,
) -> None:
    assert svg_rectangle_to_custom_area(start, end, rotation) == [
        1000,
        2000,
        3000,
        -500,
    ]


@pytest.mark.parametrize(
    "point",
    [
        (math.nan, 0.0),
        (0.0, math.inf),
        (-math.inf, 0.0),
        (1e100, 0.0),
    ],
)
def test_svg_point_to_device_invalid(point: tuple[float, float]) -> None:
    with pytest.raises(
        ValueError,
        match=r"Point coordinates must be finite|device coordinate is out of range",
    ):
        svg_point_to_device(point, RotationAngle.DEG_0)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ((1.0, 2.0), (1.0, 3.0)),
        ((1.0, 2.0), (3.0, 2.0)),
        ((1.0, 1.0), (1.001, 2.0)),
    ],
)
def test_svg_rectangle_to_custom_area_zero_area(
    start: tuple[float, float], end: tuple[float, float]
) -> None:
    with pytest.raises(
        ValueError, match="Rectangle must have non-zero width and height"
    ):
        svg_rectangle_to_custom_area(start, end, RotationAngle.DEG_0)


@pytest.mark.parametrize(
    ("value", "expected_error", "expected_log"),
    [
        (
            "invalid_base64",
            "Invalid symbol 95, offset 7.",
            "Failed to extract trace points: Invalid symbol 95, offset 7.;value:invalid_base64",
        ),
        (
            "",
            "Invalid 7z compressed data",
            "Failed to extract trace points: Invalid 7z compressed data;value:",
        ),
    ],
)
def test_MapData_add_trace_points_invalid(
    value: str, expected_error: str, expected_log: str
) -> None:
    """Test invalid MapData.add_trace_points."""
    map_data = MapData()
    with pytest.raises(ValueError, match=expected_error), LogCapture() as log:
        map_data.trace_points.add(value)
    log.check_present(
        (
            "deebot_client.map.points",
            "ERROR",
            expected_log,
        )
    )


@pytest.mark.parametrize(
    ("index", "base64_data", "expected_error", "expected_log"),
    [
        (
            10000,
            "invalid_base64",
            "Index out of bounds",
            "Index out of bounds; index:10000, base64_data:invalid_base64",
        ),
        (
            1,
            "invalid_base64",
            "Invalid symbol 95, offset 7.",
            "Failed to update map piece: Invalid symbol 95, offset 7.; index:1, base64_data:invalid_base64",
        ),
        (
            1,
            "",
            "Invalid 7z compressed data",
            "Failed to update map piece: Invalid 7z compressed data; index:1, base64_data:",
        ),
    ],
)
def test_MapData_update_map_piece_invalid(
    index: int, base64_data: str, expected_error: str, expected_log: str
) -> None:
    """Test invalid MapData.update_map_piece."""
    map_data = MapData()
    with pytest.raises(ValueError, match=expected_error), LogCapture() as log:
        map_data.background_image.update_map_piece(index, base64_data)
    log.check_present(
        (
            "deebot_client.map.background_image",
            "ERROR",
            expected_log,
        )
    )


def test_MapData_map_piece_crc32_indicates_update_invalid() -> None:
    """Test invalid MapData.map_piece_crc32_indicates_update."""
    map_data = MapData()
    with pytest.raises(ValueError, match="Index out of bounds"), LogCapture() as log:
        map_data.background_image.map_piece_crc32_indicates_update(1000, 1)
    log.check_present(
        (
            "deebot_client.map.background_image",
            "ERROR",
            "Index out of bounds; index:1000, crc32:1",
        )
    )


def test_PositionType_eq() -> None:
    """Test PositionType equality."""
    assert PositionType.DEEBOT == PositionType.DEEBOT
    assert PositionType.DEEBOT == 0

    assert PositionType.CHARGER == PositionType.CHARGER
    assert PositionType.CHARGER == 1

    assert PositionType.DEEBOT != PositionType.CHARGER
