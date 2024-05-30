from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import ANY, AsyncMock, Mock, call, patch

import pytest
from svg import (
    ArcRel,
    ClosePath,
    CubicBezier,
    HorizontalLineToRel,
    LineToRel,
    MoveTo,
    MoveToRel,
    PathData,
    Polygon,
    Scale,
    SmoothCubicBezierRel,
    Use,
    VerticalLineToRel,
    ViewBoxSpec,
)

from deebot_client.events.map import (
    MajorMapEvent,
    MapChangedEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
    Position,
    PositionsEvent,
    PositionType,
)
from deebot_client.map import (
    Map,
    MapData,
    Path,
    Point,
    TracePoint,
    _calc_point,
    _calc_point_in_viewbox,
    _get_svg_positions,
    _get_svg_subset,
    _points_to_svg_path,
)
from deebot_client.models import Room

from .common import block_till_done

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deebot_client.event_bus import EventBus

_test_calc_point_data = [
    (5000, 0, Point(100.0, 0.0)),
    (20010, -29900, Point(400.2, 598.0)),
    (None, 29900, Point(0, -598.0)),
]


@pytest.mark.parametrize(("x", "y", "expected"), _test_calc_point_data)
def test_calc_point(
    x: int,
    y: int,
    expected: Point,
) -> None:
    result = _calc_point(x, y)
    assert result == expected


_test_calc_point_in_viewbox_data = [
    (100, 100, ViewBoxSpec(-100, -100, 200, 150), Point(2.0, -2.0)),
    (-64000, -64000, ViewBoxSpec(0, 0, 1000, 1000), Point(0.0, 1000.0)),
    (64000, 64000, ViewBoxSpec(0, 0, 1000, 1000), Point(1000.0, 0.0)),
    (None, 1000, ViewBoxSpec(-500, -500, 1000, 1000), Point(0.0, -20.0)),
]


@pytest.mark.parametrize(
    ("x", "y", "viewbox", "expected"), _test_calc_point_in_viewbox_data
)
def test_calc_point_in_viewbox(
    x: int,
    y: int,
    viewbox: ViewBoxSpec,
    expected: Point,
) -> None:
    result = _calc_point_in_viewbox(x, y, viewbox)
    assert result == expected


async def test_MapData(event_bus: EventBus) -> None:
    mock = AsyncMock()
    event_bus.subscribe(MapChangedEvent, mock)

    map_data = MapData(event_bus)

    async def test_cycle() -> None:
        for x in range(10000):
            map_data.positions.append(Position(PositionType.DEEBOT, x, x, 0))
            map_data.rooms[x] = Room("test", x, "1,2")

        assert map_data.changed is True
        mock.assert_called_once()

        await asyncio.sleep(1.1)
        assert mock.call_count == 2

    await test_cycle()

    mock.reset_mock()
    map_data.reset_changed()
    await asyncio.sleep(1.1)

    await test_cycle()


async def test_Map_subscriptions(
    execute_mock: AsyncMock, event_bus_mock: Mock, event_bus: EventBus
) -> None:
    map = Map(execute_mock, event_bus_mock)

    calls = [call(MapSetEvent, ANY), call(MapSubsetEvent, ANY)]
    event_bus_mock.subscribe.assert_has_calls(calls)
    event_bus_mock.add_on_subscription_callback.assert_called_once_with(
        MapChangedEvent, ANY
    )
    # +1 is for the on_first_subscription call
    num_unsubs = len(calls) + 1
    assert len(map._unsubscribers) == num_unsubs

    async def on_change() -> None:
        pass

    event_unsub = event_bus_mock.subscribe(MapChangedEvent, on_change)
    await block_till_done(event_bus)

    events = [MajorMapEvent, MinorMapEvent, PositionsEvent, MapTraceEvent]

    calls.append(call(MapChangedEvent, on_change))
    calls.extend([call(event, ANY) for event in events])
    event_bus_mock.subscribe.assert_has_calls(calls)
    assert len(map._unsubscribers) == num_unsubs
    for event in events:
        assert event_bus.has_subscribers(event)

    event_unsub()
    for event in events:
        assert not event_bus.has_subscribers(event)

    await map.teardown()
    assert not map._unsubscribers


@patch(
    "deebot_client.util.decompress_7z_base64_data",
    Mock(return_value=b"\x10\x00\x00\x01\x00"),
)
async def test_Map_svg_traces_path(
    execute_mock: AsyncMock, event_bus_mock: Mock
) -> None:
    map = Map(execute_mock, event_bus_mock)

    path = map._get_svg_traces_path()
    assert path is None

    map._update_trace_points("")
    path = map._get_svg_traces_path()

    assert path == Path(
        fill="none",
        stroke="#fff",
        stroke_width=1.5,
        stroke_linejoin="round",
        vector_effect="non-scaling-stroke",
        transform=[
            Scale(0.2, -0.2),
        ],
        d=[MoveTo(x=16, y=256)],
    )


def test_compact_path() -> None:
    """Test that the path is compacted correctly."""
    path = Path(
        fill="#ffe605",
        d=[
            MoveTo(4, -6.4),
            CubicBezier(4, -4.2, 0, 0, 0, 0),
            SmoothCubicBezierRel(-4, -4.2, -4, -6.4),
            LineToRel(0, -3.2),
            LineToRel(4, 0),
            ArcRel(1, 2, 3, large_arc=True, sweep=False, dx=4, dy=5),
            ClosePath(),
        ],
    )

    assert (
        str(path)
        == '<path d="M4-6.4C4-4.2 0 0 0 0s-4-4.2-4-6.4l0-3.2 4 0a1 2 3 1 0 4 5Z" fill="#ffe605"/>'
    )


@pytest.mark.parametrize(
    ("points", "expected"),
    [
        (
            [Point(x=45.58, y=176.12), Point(x=18.78, y=175.94)],
            [MoveTo(45.58, 176.12), LineToRel(-26.8, -0.18)],
        ),
        (
            [
                TracePoint(x=-215, y=-70, connected=False),
                TracePoint(x=-215, y=-70, connected=True),
                TracePoint(x=-212, y=-73, connected=True),
                TracePoint(x=-213, y=-73, connected=True),
                TracePoint(x=-227, y=-72, connected=True),
                TracePoint(x=-227, y=-70, connected=True),
                TracePoint(x=-227, y=-70, connected=True),
                TracePoint(x=-256, y=-69, connected=False),
                TracePoint(x=-260, y=-80, connected=True),
            ],
            [
                MoveTo(x=-215, y=-70),
                LineToRel(dx=3, dy=-3),
                HorizontalLineToRel(dx=-1),
                LineToRel(dx=-14, dy=1),
                VerticalLineToRel(dy=2),
                MoveToRel(dx=-29, dy=1),
                LineToRel(dx=-4, dy=-11),
            ],
        ),
    ],
)
def test_points_to_svg_path(
    points: Sequence[Point | TracePoint], expected: list[PathData]
) -> None:
    assert _points_to_svg_path(points) == expected


@pytest.mark.parametrize(
    ("subset", "expected"),
    [
        (
            MapSubsetEvent(
                id=0, type=MapSetType.VIRTUAL_WALLS, coordinates="[-3900,668,-2133,668]"
            ),
            Path(
                stroke="#f00000",
                stroke_width=1.5,
                stroke_dasharray=[4],
                vector_effect="non-scaling-stroke",
                d=[MoveTo(x=-78.0, y=-13.36), HorizontalLineToRel(dx=35.34)],
            ),
        ),
        (
            MapSubsetEvent(
                id=1,
                type=MapSetType.NO_MOP_ZONES,
                coordinates="[-442,2910,-442,982,1214,982,1214,2910]",
            ),
            Polygon(
                fill="#ffa50030",
                stroke="#ffa500",
                stroke_width=1.5,
                stroke_dasharray=[4],
                vector_effect="non-scaling-stroke",
                points=[-8.84, -58.2, -8.84, -19.64, 24.28, -19.64, 24.28, -58.2],
            ),
        ),
    ],
)
def test_get_svg_subset(subset: MapSubsetEvent, expected: Path | Polygon) -> None:
    assert _get_svg_subset(subset) == expected


_test_get_svg_positions_data = [
    (
        [Position(PositionType.CHARGER, 5000, -55000, 0)],
        ViewBoxSpec(-500, -500, 1000, 1000),
        [Use(href="#c", x=100, y=500)],
    ),
    (
        [Position(PositionType.DEEBOT, 15000, 15000, 0)],
        ViewBoxSpec(-500, -500, 1000, 1000),
        [Use(href="#d", x=300, y=-300)],
    ),
    (
        [
            Position(PositionType.CHARGER, 25000, 55000, 0),
            Position(PositionType.DEEBOT, -5000, -50000, 0),
        ],
        ViewBoxSpec(-500, -500, 1000, 1000),
        [Use(href="#d", x=-100, y=500), Use(href="#c", x=500, y=-500)],
    ),
    (
        [
            Position(PositionType.DEEBOT, -10000, 10000, 0),
            Position(PositionType.CHARGER, 50000, 5000, 0),
        ],
        ViewBoxSpec(-500, -500, 1000, 1000),
        [Use(href="#d", x=-200, y=-200), Use(href="#c", x=500, y=-100)],
    ),
]


@pytest.mark.parametrize(
    ("positions", "viewbox", "expected"), _test_get_svg_positions_data
)
def test_get_svg_positions(
    positions: list[Position],
    viewbox: ViewBoxSpec,
    expected: list[Use],
) -> None:
    result = _get_svg_positions(positions, viewbox)
    assert result == expected
