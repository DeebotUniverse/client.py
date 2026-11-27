"""Native raster, vector layers and viewport must share the same rotation."""

from __future__ import annotations

import base64
from xml.etree import ElementTree as ET

import pytest

from deebot_client.events.map import MapSetType, MapSubsetEvent, Position
from deebot_client.rs.map import MapData, PositionType, RotationAngle


@pytest.mark.parametrize(
    ("rotation", "bounds", "robot", "dock"),
    [
        (RotationAngle.DEG_0, (2, 4, 6, 3), (3, 5), (7, 6)),
        (RotationAngle.DEG_90, (-7, 2, 3, 6), (-5, 3), (-6, 7)),
        (RotationAngle.DEG_180, (-8, -7, 6, 3), (-3, -5), (-7, -6)),
        (RotationAngle.DEG_270, (4, -8, 3, 6), (5, -3), (6, -7)),
    ],
)
def test_native_layers_rotate_together(
    rotation: RotationAngle,
    bounds: tuple[int, int, int, int],
    robot: tuple[int, int],
    dock: tuple[int, int],
) -> None:
    data = MapData()
    pixels = bytes([0xFF, 0, 1, 0, 0, 0] + [0] * 6 + [0, 2, 0, 0, 0, 3])
    raster = base64.b64encode(bytes([0xF0, 3]) + pixels).decode()
    data.background_image.set_native_raster(raster, 6, 3, 402, 406, 5)
    trace = b"\x0f\x00\xe7\xff\x80\x23\x00\xe2\xff\x00"
    data.trace_points.set_native(base64.b64encode(b"\xa0" + trace).decode(), 10, 0, 2)
    positions = [
        Position(PositionType.DEEBOT, 150, -250, 0),
        Position(PositionType.CHARGER, 350, -300, 0),
    ]
    wall = MapSubsetEvent(1, MapSetType.VIRTUAL_WALLS, "[150,-250,350,-300]")

    svg = data.generate_svg([wall], positions, rotation)
    assert svg is not None
    root = ET.fromstring(svg)  # noqa: S314 - generated synthetic SDK output, not untrusted XML
    x, y, width, height = bounds
    assert tuple(map(int, root.attrib["viewBox"].split())) == (
        x - 12,
        y - 12,
        width + 24,
        height + 24,
    )
    image = root.find("{*}image")
    assert image is not None
    assert tuple(image.attrib[k] for k in ("x", "y", "width", "height")) == (
        "2",
        "4",
        "6",
        "3",
    )
    angle = {
        RotationAngle.DEG_0: 0,
        RotationAngle.DEG_90: 90,
        RotationAngle.DEG_180: 180,
        RotationAngle.DEG_270: 270,
    }[rotation]
    assert image.attrib.get("transform") == (f"rotate({angle})" if angle else None)
    markers = {node.attrib["href"]: node for node in root.findall("{*}use")}
    assert tuple(float(markers["#d"].attrib[k]) for k in ("x", "y")) == robot
    assert tuple(float(markers["#c"].attrib[k]) for k in ("x", "y")) == dock
    overlay = root.find("{*}g/{*}path[@class='v']")
    assert overlay is not None
    separator = " " if robot[1] >= 0 else ""
    assert overlay.attrib["d"].startswith(f"M{robot[0]}{separator}{robot[1]}")
    trajectory = root.find("{*}path[@transform='scale(0.2-0.2)']")
    assert trajectory is not None
    trace_x, trace_y = robot[0] * 5, -robot[1] * 5
    separator = " " if trace_y >= 0 else ""
    assert trajectory.attrib["d"].startswith(f"M{trace_x}{separator}{trace_y}")


def test_native_rotation_handles_minimum_valid_canvas_coordinate() -> None:
    data = MapData()
    raster = base64.b64encode(b"\x10\x00").decode()
    data.background_image.set_native_raster(raster, 1, 1, -32368, 400, 5)
    svg = data.generate_svg([], [], RotationAngle.DEG_180)
    assert svg is not None
    root = ET.fromstring(svg)  # noqa: S314 - generated synthetic SDK output, not untrusted XML
    assert tuple(map(int, root.attrib["viewBox"].split())) == (32755, -13, 25, 25)
