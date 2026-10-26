"""Test rust map module."""

from __future__ import annotations

import pytest
from testfixtures import LogCapture

from deebot_client.events.map import MapInfoEvent
from deebot_client.rs.map import MapData, PositionType, RotationAngle
from tests.data.map.test_4 import EVENTS as MAP_INFO_EVENTS


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


def test_MapData_generate_svg_without_subsets_and_positions() -> None:
    """Test MapData.generate_svg with only map info."""
    map_info = next(e for e in MAP_INFO_EVENTS if isinstance(e, MapInfoEvent))
    map_data = MapData()
    map_data.map_info.set(map_info.info)

    svg = map_data.generate_svg([], [], RotationAngle.DEG_0)

    assert svg is not None
    assert svg.startswith("<svg")
    assert "<use" not in svg
