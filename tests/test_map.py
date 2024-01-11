import asyncio
from collections.abc import Sequence
from unittest.mock import ANY, AsyncMock, Mock, call

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
    SmoothCubicBezierRel,
    VerticalLineToRel,
)

from deebot_client.event_bus import EventBus
from deebot_client.events.map import (
    MapChangedEvent,
    MapSetEvent,
    MapSubsetEvent,
    Position,
    PositionType,
)
from deebot_client.map import (
    AxisManipulation,
    Map,
    MapData,
    MapManipulation,
    Path,
    Point,
    TracePoint,
    _calc_point,
    _points_to_svg_path,
)
from deebot_client.models import Room

_test_calc_point_data = [
    (10, 100, (100, 0, 200, 50), Point(100.0, 0.0)),
    (10, 100, (0, 0, 1000, 1000), Point(400.2, 598.0)),
    (None, 100, (0, 0, 1000, 1000), Point(0, 598.0)),
]


@pytest.mark.parametrize(("x", "y", "image_box", "expected"), _test_calc_point_data)
def test_calc_point(
    x: int,
    y: int,
    image_box: tuple[int, int, int, int],
    expected: Point,
) -> None:
    manipulation = MapManipulation(
        AxisManipulation(
            map_shift=image_box[0],
            svg_max=image_box[2] - image_box[0],
        ),
        AxisManipulation(
            map_shift=image_box[1],
            svg_max=image_box[3] - image_box[1],
            _transform=lambda c, v: 2 * c - v,
        ),
    )
    result = _calc_point(x, y, manipulation)
    assert result == expected


@pytest.mark.parametrize(("error"), [ValueError(), ZeroDivisionError()])
def test_calc_point_exceptions(
    error: Exception,
) -> None:
    def transform(_: float, __: float) -> float:
        raise error

    manipulation = MapManipulation(
        AxisManipulation(
            map_shift=50,
            svg_max=100,
            _transform=transform,
        ),
        AxisManipulation(
            map_shift=50,
            svg_max=100,
        ),
    )
    result = _calc_point(100, 100, manipulation)
    assert result == Point(0, 100)


async def test_MapData(event_bus: EventBus) -> None:
    mock = AsyncMock()
    event_bus.subscribe(MapChangedEvent, mock)

    map_data = MapData(event_bus)

    async def test_cycle() -> None:
        for x in range(10000):
            map_data.positions.append(Position(PositionType.DEEBOT, x, x, -1))
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


async def test_Map_internal_subscriptions(
    execute_mock: AsyncMock, event_bus_mock: Mock
) -> None:
    map = Map(execute_mock, event_bus_mock)

    calls = [call(MapSetEvent, ANY), call(MapSubsetEvent, ANY)]
    event_bus_mock.subscribe.assert_has_calls(calls)
    assert len(map._unsubscribers_internal) == len(calls)

    await map.teardown()
    assert not map._unsubscribers_internal


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
