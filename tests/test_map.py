from __future__ import annotations

import asyncio
import platform
from typing import TYPE_CHECKING
from unittest.mock import ANY, AsyncMock, Mock, call

import pytest

from deebot_client.events.map import (
    CachedMapInfoEvent,
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
)
from deebot_client.models import Room

from .common import block_till_done

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_codspeed import BenchmarkFixture

    from deebot_client.event_bus import EventBus
    from deebot_client.events.base import Event

# _test_calc_point_data = [
#     (5000, 0, Point(100.0, 0.0)),
#     (20010, -29900, Point(400.2, 598.0)),
#     (None, 29900, Point(0, -598.0)),
# ]


# @pytest.mark.parametrize(("x", "y", "expected"), _test_calc_point_data)
# def test_calc_point(
#     x: int,
#     y: int,
#     expected: Point,
# ) -> None:
#     result = _calc_point(x, y)
#     assert result == expected


# _test_calc_point_in_viewbox_data = [
#     (100, 100, ViewBoxSpec(-100, -100, 200, 150), Point(2.0, -2.0)),
#     (-64000, -64000, ViewBoxSpec(0, 0, 1000, 1000), Point(0.0, 1000.0)),
#     (64000, 64000, ViewBoxSpec(0, 0, 1000, 1000), Point(1000.0, 0.0)),
#     (None, 1000, ViewBoxSpec(-500, -500, 1000, 1000), Point(0.0, -20.0)),
# ]


# @pytest.mark.parametrize(
#     ("x", "y", "view_box", "expected"), _test_calc_point_in_viewbox_data
# )
# def test_calc_point_in_viewbox(
#     x: int,
#     y: int,
#     view_box: ViewBoxSpec,
#     expected: Point,
# ) -> None:
#     result = _calc_point_in_viewbox(x, y, ViewBoxFloat(view_box))
#     assert result == expected


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


def _test_Map_subscriptions_subscribe(event_bus_mock: Mock) -> None:
    async def on_cached_info(_: CachedMapInfoEvent) -> None:
        pass

    event_bus_mock.subscribe(CachedMapInfoEvent, on_cached_info)
    event_bus_mock.subscribe.reset_mock()


@pytest.mark.parametrize(
    ("prepare_fn", "events_with_subscriber"),
    [(lambda _: None, []), (_test_Map_subscriptions_subscribe, [CachedMapInfoEvent])],
    ids=["No CachedMapInfoEvent subscribers", "Already CachedMapInfoEvent subscribers"],
)
async def test_Map_subscriptions(
    execute_mock: AsyncMock,
    event_bus_mock: Mock,
    event_bus: EventBus,
    prepare_fn: Callable[[Mock], None],
    events_with_subscriber: list[type[Event]],
) -> None:
    prepare_fn(event_bus_mock)
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

    events = [
        MajorMapEvent,
        MinorMapEvent,
        CachedMapInfoEvent,
        PositionsEvent,
        MapTraceEvent,
    ]

    calls.append(call(MapChangedEvent, on_change))
    calls.extend([call(event, ANY) for event in events])
    event_bus_mock.subscribe.assert_has_calls(calls)
    assert len(map._unsubscribers) == num_unsubs
    for event in events:
        assert event_bus.has_subscribers(event)

    event_unsub()
    for event in events:
        if event not in events_with_subscriber:
            assert not event_bus.has_subscribers(event)

    await map.teardown()
    assert not map._unsubscribers


# async def test_Map_svg_traces_path(
#     execute_mock: AsyncMock, event_bus_mock: Mock
# ) -> None:
#     map = Map(execute_mock, event_bus_mock)

#     path = map._get_svg_traces_path()
#     assert path is None

#     # Normally trace points would be added by MapTraceEvent
#     map._map_data.trace_values.append(TracePoint(x=16, y=256, connected=True))
#     path = map._get_svg_traces_path()

#     assert path == Path(
#         fill="none",
#         stroke="#fff",
#         stroke_width=1.5,
#         stroke_linejoin="round",
#         vector_effect="non-scaling-stroke",
#         transform=[
#             Scale(0.2, -0.2),
#         ],
#         d=[MoveTo(x=16, y=256)],
#     )


# def test_compact_path() -> None:
#     """Test that the path is compacted correctly."""
#     path = Path(
#         fill="#ffe605",
#         d=[
#             MoveTo(4, -6.4),
#             CubicBezier(4, -4.2, 0, 0, 0, 0),
#             SmoothCubicBezierRel(-4, -4.2, -4, -6.4),
#             LineToRel(0, -3.2),
#             LineToRel(4, 0),
#             ArcRel(1, 2, 3, large_arc=True, sweep=False, dx=4, dy=5),
#             ClosePath(),
#         ],
#     )

#     assert (
#         str(path)
#         == '<path d="M4-6.4C4-4.2 0 0 0 0s-4-4.2-4-6.4l0-3.2 4 0a1 2 3 1 0 4 5Z" fill="#ffe605"/>'
#     )


# @pytest.mark.parametrize(
#     ("points", "expected"),
#     [
#         (
#             [Point(x=45.58, y=176.12), Point(x=18.78, y=175.94)],
#             [MoveTo(45.58, 176.12), LineToRel(-26.8, -0.18)],
#         ),
#         (
#             [
#                 TracePoint(x=-215, y=-70, connected=False),
#                 TracePoint(x=-215, y=-70, connected=True),
#                 TracePoint(x=-212, y=-73, connected=True),
#                 TracePoint(x=-213, y=-73, connected=True),
#                 TracePoint(x=-227, y=-72, connected=True),
#                 TracePoint(x=-227, y=-70, connected=True),
#                 TracePoint(x=-227, y=-70, connected=True),
#                 TracePoint(x=-256, y=-69, connected=False),
#                 TracePoint(x=-260, y=-80, connected=True),
#             ],
#             [
#                 MoveTo(x=-215, y=-70),
#                 LineToRel(dx=3, dy=-3),
#                 HorizontalLineToRel(dx=-1),
#                 LineToRel(dx=-14, dy=1),
#                 VerticalLineToRel(dy=2),
#                 MoveToRel(dx=-29, dy=1),
#                 LineToRel(dx=-4, dy=-11),
#             ],
#         ),
#     ],
# )
# def test_points_to_svg_path(
#     points: Sequence[Point | TracePoint], expected: list[PathData]
# ) -> None:
#     assert _points_to_svg_path(points) == expected


# @pytest.mark.parametrize(
#     ("subset", "expected"),
#     [
#         (
#             MapSubsetEvent(
#                 id=0, type=MapSetType.VIRTUAL_WALLS, coordinates="[-3900,668,-2133,668]"
#             ),
#             Path(
#                 stroke="#f00000",
#                 stroke_width=1.5,
#                 stroke_dasharray=[4],
#                 vector_effect="non-scaling-stroke",
#                 d=[MoveTo(x=-78.0, y=-13.36), HorizontalLineToRel(dx=35.34)],
#             ),
#         ),
#         (
#             MapSubsetEvent(
#                 id=1,
#                 type=MapSetType.NO_MOP_ZONES,
#                 coordinates="[-442,2910,-442,982,1214,982,1214,2910]",
#             ),
#             Polygon(
#                 fill="#ffa50030",
#                 stroke="#ffa500",
#                 stroke_width=1.5,
#                 stroke_dasharray=[4],
#                 vector_effect="non-scaling-stroke",
#                 points=[-8.84, -58.2, -8.84, -19.64, 24.28, -19.64, 24.28, -58.2],
#             ),
#         ),
#         (
#             MapSubsetEvent(
#                 id=0,
#                 type=MapSetType.VIRTUAL_WALLS,
#                 coordinates="['12023', '1979', '12135', '-6720']",
#             ),
#             Path(
#                 stroke="#f00000",
#                 stroke_width=1.5,
#                 stroke_dasharray=[4],
#                 vector_effect="non-scaling-stroke",
#                 d=[MoveTo(x=240.46, y=-39.58), LineToRel(dx=2.24, dy=173.98)],
#             ),
#         ),
#     ],
# )
# def test_get_svg_subset(subset: MapSubsetEvent, expected: Path | Polygon) -> None:
#     assert _get_svg_subset(subset) == expected


# _test_get_svg_positions_data = [
#     (
#         [Position(PositionType.CHARGER, 5000, -55000, 0)],
#         ViewBoxSpec(-500, -500, 1000, 1000),
#         [Use(href="#c", x=100, y=500)],
#     ),
#     (
#         [Position(PositionType.DEEBOT, 15000, 15000, 0)],
#         ViewBoxSpec(-500, -500, 1000, 1000),
#         [Use(href="#d", x=300, y=-300)],
#     ),
#     (
#         [
#             Position(PositionType.CHARGER, 25000, 55000, 0),
#             Position(PositionType.DEEBOT, -5000, -50000, 0),
#         ],
#         ViewBoxSpec(-500, -500, 1000, 1000),
#         [Use(href="#d", x=-100, y=500), Use(href="#c", x=500, y=-500)],
#     ),
#     (
#         [
#             Position(PositionType.DEEBOT, -10000, 10000, 0),
#             Position(PositionType.CHARGER, 50000, 5000, 0),
#         ],
#         ViewBoxSpec(-500, -500, 1000, 1000),
#         [Use(href="#d", x=-200, y=-200), Use(href="#c", x=500, y=-100)],
#     ),
# ]


# @pytest.mark.parametrize(
#     ("positions", "view_box", "expected"), _test_get_svg_positions_data
# )
# def test_get_svg_positions(
#     positions: list[Position],
#     view_box: ViewBoxSpec,
#     expected: list[Use],
# ) -> None:
#     result = _get_svg_positions(positions, ViewBoxFloat(view_box))
#     assert result == expected


def test_get_svg_map(
    event_loop: asyncio.AbstractEventLoop,
    benchmark: BenchmarkFixture,
    execute_mock: AsyncMock,
    event_bus: EventBus,
) -> None:
    """Test getting svg map."""

    async def on_change(_: MapChangedEvent) -> None:
        pass

    async def test_fn() -> str | None:
        map = Map(execute_mock, event_bus)
        event_bus.subscribe(MapChangedEvent, on_change)
        await block_till_done(event_bus)

        for event in _events_for_map_test():
            event_bus.notify(event)

        await block_till_done(event_bus)
        return map.get_svg_map()

    @benchmark
    def svg_map() -> str | None:
        return event_loop.run_until_complete(test_fn())

    assert svg_map == _svg_per_platform()


def _svg_per_platform() -> str:
    png = _png_per_platform()
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-26 -53 350 180"><defs ><radialGradient id="dbg" cx="50%" cy="50%" r="50%" fx="50%" fy="50%"><stop style="stop-color:#00f" offset="70%"/><stop style="stop-color:#00f0" offset="97%"/></radialGradient><g id="d"><circle r="5" fill="url(#dbg)"/><circle stroke="white" stroke-width="0.5" r="3.5" fill="blue"/></g><g id="c"><path d="M4-6.4C4-4.2 0 0 0 0s-4-4.2-4-6.4 1.8-4 4-4 4 1.8 4 4Z" fill="#ffe605"/><circle cy="-6.4" r="2.8" fill="#fff"/></g></defs><image style="image-rendering: pixelated" href="data:image/png;base64,{png}" x="-26" y="-53" width="350" height="180"/><path stroke="#f00000" stroke-dasharray="4" stroke-width="1.5" vector-effect="non-scaling-stroke" d="M240.46-39.58l2.24 173.98"/><path stroke="#f00000" stroke-dasharray="4" stroke-width="1.5" vector-effect="non-scaling-stroke" d="M42.4 91.62l-0.28 33.8"/><path stroke="#fff" stroke-width="1.5" vector-effect="non-scaling-stroke" transform="scale(0.2 -0.2)" d="M0 1l-10-1h-10l7-7 8-7 5-9 5-8h11l10 1 11-2 8-6 6-8 4-9-3-10-5-9-5-8-11-2h-10l-9 3-8 7-4 9-2 10 3 9 5 9-5 9 8-6 5 9 9 4 10-2 6-8 8-6 5-9 2-10-3-10-4-10-6-7-10-2h-11l-9 4-8 7-4 9-1 10-8-6-3-10 7-8 6-7 7-7 9-4 10-1 9 4 11 1 10-1 9-4h10l10-1 10-1 9-5 8-8 2-10-2-10 4-9 10-3 11-1 10 1 7 7-3 10-3 9-4 11-3 9-3 10-4 10-2 10 5 9 8 6 10 2 10-1 6-7 5-9 2-10 2-10 4-10 9-5 10 1h10 11l8 6 3 10 1 10v10 10 10 11 10 10l1 11-7 7h-10l-9 4-9 5-6 8-2 10 6 8 10 3-5 9-2 10 2 10-10 3-10-2-8 6-5 9 3 9v11l2 9 9 5h11 10l10-3 6-8 1-10-2-10 5-8 9-5 8 8 10 1 9-4 6-8 4-9-1-10v-10l10-1 10-2h10 10 10l6 8-1 10-8 7h-10l-9 5-10 2-10 1-9 5-5 9-2 10 1 10 6 8 9 4 10 2 10-3 8-5 6-9h10l2 10 3 10-1 10 1 10v11l1 10-6 8h-11l-5-8-8-6h-10l-10 3-10 4-5 9 1 10 1 10 7 7v11l-1 10-5 8-10 2-10 1h-10l-10 1-10-1h-11-10-10l-5-9-2-9-2-10-9-4-10-1-10 4-5 9-2 10 1 10-10 1-10 2h-10-10l-11 1h-10l6-8 4-10v-10l-5-9-5-8-6-9-9-4-10-3-9 3-9 5-8 7-2-10-6-8-8-7h-10l-9 1-10 1h-10l-10-2-10 2-10-1-10 1h-10l-10 1-8-6v-11l-2-10v-10l1-10v-11-10-10l-1-10 5-9 7-7 4-9-3-10-3-10-8-5-1-10v-10l7-8 7-6 7-7 8 5-5 8-7 7-5 10-1 10 2 10 7 8 10 3 10 3 10-2 8-7 6-8 2-10-2-10-1-10 8-7 8-5 9-5 8-3 7-7 11-1h10l7-8 7-7 8-6 10-4 9-5 8-6 7-8 8-6 6-8 8-7 7-8 7-7 8-7 2-10-1-10 1-5-2-5-5-2-3 9-1 11v10l1 10v11l-1 11v10l-1 11v10 10 10 10 11l1 9-1 10 1 10-1 10v11l1 10 1 10v11 10 11l-1 10v11 10 10l1 11-1 11v11l-1 10 1 11v10 11 8l5-1 5-3 1-10-1-10 1-11v-10-11-10l1-10v-10-10-10-11l1-10v-10l1-11-1-10v-10l-2-10v-10l-1-10v-11l-1-10 1-10 1-11v-10-10-5h6l4 2 4 10v10l-1 10v11l-1 9v11 10l1 10v11 10 11 10 10 11l-1 10 1 11-1 10v11l1 10-1 10v11 10l1 5 1 5 4 3 5 2 4-10v-11-10l-1-11v-10-11-10-10l1-11v-10-10-11-10l-1-10v-11-10l1-10-1-10v-11-9-10-10-10l2-5 6-1 5-2v10 10l-1 11v10l-1 9 1 10-1 11 1 10-1 10 1 11-1 5 5-2 5-2 5-2-1-10v-11-10-10-11-10-10-11-10-10-11-10-9l3-5 4-3 4-3v10 11 10l-1 10v11l1 10v10 10 5l5-2 4-2 4-3 1-11 1-10v-10-11-10-11-10-6l4-3 5-2 2 10v11 10 10l-1 10-1 10 1 11-4 9-9 4-9 6-9 4-8 5-9 5-4 10-2 10v10 10l1 11v10 10l1 11 1 10 1 11v5 11 10 11 10l1 10-1 11 2 4 4 4-1-5 1-5 1-5v-5l-1-5 1-5 3-5 4-3-2-10v-11-5l3-4 4-4 5 1 1 10-1 11v10l-5 9-9 5-4 10-1 10 1 10 5 9 9 4 10-1 10-1 10-3 5-9-1-10-1-10-2-10-8-6-10 1-10-1h10l11 1 7 6 5 9 1 10-1 10-5 10-4 9-3 4h7l-10-1h-11l5-9 9-4 8-6 3-10 1-10-2-10-4-9-5-9-3-5-1-10v-6l2-4 5-2 4 9-1 11 5 1h5l4-10v-10-11-10-10l1-6-1 10-1 10v10 11 10 10l-1 11 1 10v10l1 10-1 10 1 6 3 5 4 3 4 4v-10-11-10-10-11-10-10-11l1-10-1-10 1-10v-9l3 4 2 5 2 4 3 5v11 11l1 10-1 11v5l5-1 4-4 4-3 1-10v-11-5l2-5 5-3 5 1v11 10 6l2 5 2 4 5 2 5-3-1-10v-10-6l5-2 5-2 4-2-1 10v10 8l2 5 4 2v-10-11l-1-10-9-3h-11-10-10-10-11l-8-6 4-10 3-10 3-10 7-8 8-7 2-10 9-4 2-7v-5l4-4h5l4 9-8 7-9 5-7 7-7 7-8 6-5 9-1 10-1 11 1 10 1 10v10l1 11 1 10v10l1 11 1 10 2 5 1 10 1 10-5-10-5-9-4-10-4-9-6-10-5-8-6-8-6-9-7-8-10 1-10 1-10 4-9 4-9 5-9 5-9 5-8 8-5 9-6 8-6 8-4 10-4 4-5 2 1 6v-10l-1-12 1-10-1-10 1-11v-10l1-11-1-10 1-10-1-11 1-10v-10-11-10l-1-10v-10-10l-2-10v-11-10l1-10v-10-10-10l1-11v-10l1-10-1-10 1-11v-10-6l-5 3-4 2-2 10-1 11v10 10 10l-1 11 1 10-1 10-1 10-1 10v11l1 10v11 10l1 10-1 11 1 10 1 10v10 11l1 10-2 10 1 11-1 10v10l-1 11 1 10v10l1 11 1 10-3-10 1-10-1-10-5-9-4-3-2-10 1-10v-11l-1-10v-10l1-10v-10l-1-10-1-11-1-10v-10-10l-1-11 1-10 1-11-1-10v-10-9-11-10-10l1-11v-10-10l1-10-1-7v-5l-3-4-6-2-2 9v10 10 11l-1 10 1 10-1 10-1 10v10l1 10v10 11l1 10-1 10 1 11v10 11 10 10l-1 10 1 10v11l1 10v11l-1 10v6l-5-2-5-2-3-10v-10l-1-10-2-10-1-10 1-11 1-10v-10-11l-1-10v-10l1-10-1-11 1-10v-11l-1-9v-11-10-11l1-10 1-10v-11-10 10l-1 10-1 11-3 10-3 9-2 10-1 10-1 10 1 10-1 10 1 10-1 11 1 10v10 10 10 11 11 10 10 10 11 10 6 6l-3 3-5 3-5-2 1-11-1-10 2-10-1-10v-11-10l-1-10-1-11v-10-10l-1-10v-10-11l1-10v-10l1-11-1-10v-9-5l-3-4-4-3-5 9-1 11 1 9v10l-1 10-1 10-1 11v10 10l1 10v10l1 10 1 11v10l-1 10-1 10 1 11v5l-5-2-5-1-2-10 1-10-2-11v-10l1-10v-10l-1-10-1-11v-10l-1-10v-10l1-11-1-10 1-10 1-10v-5l-4 3-4 3-2 10 1 10-2 10v10 10l-1 10-1 10 1 11 1 10-1 10v10l1 10v11l1 10v7l-2 5-2 4-6 2v-11-10-10l1-11-2-10 1-10-1-10v-10-10l-1-11-1-10 1-10 1-10v-11l1-10-3 10-5 10-2 10-4 9-2 5v10l-1 10-1 11v10 10l1 11 1 10v10 10l1 10v-5l1-5 1-6 1-5v-10l-2 5-3 4-2 5-1 6-2 4-2 5-3 5 1-11 1-10v-11l-1-10 1-11v-10l1-10-2-11 1-7-1-5-4-4-5-1-5 9v11l1 10-2 10 1 11v10 10 11 10 6l-1 5-4 2-4 3-2-10v-10-10-11l1-10v-10l-1-10v-10-11-7l-5 2-4 3-5 3v10 11 10l-1 10v11 10 10 10h10l10 1h10 11l10 1 10 1 11 1h9l10 1h10 10l11 1h10l10-1 10 2h11l10 2h10l9 5v10l-3 11-3 9-2 10-2 8h10l10 1h6l5-1 3-3 2-5-10-1h-11l-10-1h-7l-4-2-1-5-4-4 10-3 10 1h10l10 1 11-1h10l10 1 10-1 6 8 8 6 10 5 10-3 7-7 7-8 2-10-2-10-4-9-10-4-10-2-10 2-7 7-5 9-1 10-5 1-5-3-4-2-11-1h-10-10l-10-1-11 1h-10-10l1-5-1-6-10-3h-10l-10-1h-10l-11-1-5 1h10 12l11 1h10l10-1h11 10 10 11l10-1 10 1h10l4-3 3-4 3-5-10 2-10-1-10-1-11 1-10-1-11 1h-10-11l-10-1-10 1h-10l-10-1h-10l-10 1h-11-11-9-10-11-10l-10-1h-11-10l-4-2-3-5-3-4 11-1 10 1h10 10 11l10 1h10 10 10l10-1h10 10l10-1 11 1 10-1h11 10 11 10 10l10 1 11-1h10 10 11 10 11l10 1 10-1h10 10l10 1h10 10 10 11l10-1 10 1h5l4 3 3 3v5l-10 1-10-3-8-6-9-5-10 1-10 4-4 3-1 5-10 1h-10l-11-1 1 5 2 5 9 4 10-1 6 2 4 4-1 5-10 1-11-1-5 1-5 2-3 4 1 5 10 1h11l5 1 1 6 3 4-10 3h-11-7l-5 2-4 3-3 4-5 3h11l10 1h10 10l4-10-2-10-1-11-1-10-2-10-1-11-1-11-1-10-1-5h11 10l11 1h10 10 11 5-10-10-11-10-10-10l-10 1h-11l-10-1h-10-11-10l-10-1-11 1h-10l-10-1h-10l-10 1h-10-11l-10-1-10 1h-11-10l-11 1h-10-10l-10 1h-10-11-9l-10-1-11-1-10 1-10-1h-11l-10 1h-10-6l-4-3-3-3-1-6 10-1h10 11 10 10 11 10 10l10-1 10 1 10-1 10 1 11-1 10 1 10-1h10 10 11l10 1 10-1h11 10 10 10 11l-2-5-2-5-4-3-10-1-10-1h-10l-11 1h-10-10-10l-10 1-10 1h-11-10-10-10-10-11-9-11-10l-10-1h-10-11l-11-1h-10-6l-5-1-3-5 9-5 10 1h10l11 1 10-1 11 1 10-1h10 9 10l11 1 10-1 10 1h10 10 11 10l10 1 11-1 10-1h10 11 10 10l5-1 5-1 4-3 2-5-10-3-10-1h-11-10-11-10l-10 2h-10-11l-10 1h-11l-10-1h-10-10l-11 1-11-1h-9-10l-10-1-11 1h-10l-11-1-10 1-10-1h-5l3-5 3-5 10-4 11 1 10 1h10 10 11 10 9 11 10 10 11l10-1 10 1h10 11 10 10 10l11-1h10l10-1 10 1 5-2 4-3 5-2 5-3 5-2h-11-10l-11-1-10-1h-11l-10 1-10 1h-11l-10 1h-10-10-10-11-10-10-10-10-10-10l-10-1-11-1 2-4 4-4 5-3 10 1h10l10 1h10l10-1h10l11 1 10-1h10 10l10 1h11 10 10 10 11l10-1 11-2 11 1 10-1 9 1-3-4-4-4-4-4-10-1-10-1h-10l-11-1h-10l-10 1 1-10-11-4-10-3-10 3-8 5 1 10 10 3 7 8 4 9 10-2 2-9-9-4-9 6 4 10 7 7 7 8 7 8 7 7 8 7 7 7 8 6 8 6 8 7 8 6 7 7 10 3 10-4 9-4 8-4h11l10-1 10 1h5v-6l-3-4-4-4h-10-10l-3-4 3-4 2-5 11 1 10-1 6-8 8-5 5-10 4-9 4-9 1-5 10-4h10l9 1 6 1 4 2 1 5-10 3h-11l-10-1-10 3-5 8-5 9-6 8-7 7-5 10-6 7-8 7-9 6-9 5-9 5-10 3h-10l-10-3-9-5-9-4-9-5-9-5-9-4-9-6-8-7-7-7-8-7-7-7-7-8-6-8-6-8-6-9-5-5-10-1-10 1h-11-10-10l-11 1-9-1h-10-5l-5-4-1-5 2-5h10 10 9 11l10 1 10 1h10 11l10-1 10-1 10-2 10-1 10 2 10-1h11l8 1h10l11 1h10 9l4-4 3-5 2-5h-10l-11-1h-10-10-11-10-11-10-11-10l-10 1-10-1h-10l-11 1-10 1h-11l-10-2h-10l-9 1-7-1 5-2 5-1 4-2 5-1 5-2 10-1h10 10l11 1h10l10 1 11-1h10l10-1h10 11l10 1 10 1h11l10-2h10l11-1 10 1 10 1 5-1 3-4 3-5 4-4-10-1h-11-10l-11-1h-10-10l-10-1h-10-11-10-10-11l-10 1-11-1-10 1h-10-10l2-5 2-4 10-1h11l10 1h10l11 1h10 11 10l10-1 11-1 10-1 10 1h10 11l10-1 11 1 6-1 5-1 4-3 1-5-10-2h-11l-10-1h-10-11-10-11l-10-1h-10-10-10-10l-10 1h-11-10-10-5l-5-2-2-4v-6h10 10 11l10 1h10l10 1 8-1 1-5-2-5-2-5-10-1h-10-11l-10 1-10-1-7 1-5-2-3-4-1-5h10 10l10 1h11 10 11l5-1 2-4 1-5 3-5-11-1-10 1 3-4 4-3 5-2 6-3-5 2 3-5 2-5 2-7 6 1 4-3v-5l-9-3-3 10 1 10v10l-1 11v10l-1 11v10 10 10l2 10h10l10-4 10-4 9-4 9-3 8-6v-6h10 10l10 1 10-1 5-1 4-3 1-5-9-3h-11-10-10l-5-1-4-3v-5l2-5h10l10 1h11l6 1 5-1 4-3 2-5-10-3-10-1h-10l-10 4-4 9-5 9-4 10-4 9-3 10-4 9-10 2-9-6-8-6-8-7-7-8-8-6-7-8-2-10v-10l3-9 3-10 4-10 5-9 3-10 4-9 4-10 2-10 2-10-1 10-5 9-10 2-2-10-5-9-9-6-9-4-10 1h-10-11-10-11l-10 1-10 1h-11-10l-10 1-10-1-10 1-10-1-11 1-10-1-8-6-10-2-10 2-5 8-10-1-10 1-2-10-2-10v-10l-1-10v-11-10-10l9-5 10-3h10 10 10l10 1 10-1 10 1 11-1h10l10-1h9 11l10-1h10l10-2 6-8 10-4 10 1 10-1 10 1 10 1 6 8 8 6 10 2h11 10l10-1h11 10l11-1h10 10 10l10-1h11 10l11-1 10 1h10l10-1h11l10-1h11l10-1 11 1 10-1 10-1 8-7 2-10 2-10 8-5 10 1 1 11 3 10 7 8 7 6 12-1 10-1 13-2h10 11l10-1h10 11 10 10l10-1h11l14-1h11l14 1h10l10-1h10 11l10 2 11-1 8-6 6-8 7-7h11l10 2h10l11-1v10l7 7 10 3h10l11-1 10-1h10 10 10l10 3 5 9 3 9-2 10 1 10v10l-1 11 1 10-10 3-10 1h-10-10-11l-10 1h-10-11l-10-1-10 1-10-1h-11-11-10l-11 1h-10l-10-1-10 1-12-1h-11l-10 1-2-10-6-8-9-5-11 1-10 3h-10-10-10l-11 1h-10-11l-10 1-9 4-4 9-9 5-9 4-10 5-1 10 2 11 4 9 4 9 6 9-10 1-11 1-9 2-7-8-6-8-4-9-5-9-3-9-5-10-7-6-11-1-10-1-10-2h-10l-10 2-10-1-10 1-10-1h-11l-10 1h-10l-10 2-10 2h-11l-10 1h-10-10-11l-10 1-10 1-7 7-4 10-1 10-10 2h-10l-8-7v-5h11 5l2-5 2-5-10-4h-10-10l-2-5 2-5 10-2h10 10l11-1 10 1h10l11-1h10 11 10 10 5l-11 1h-10-10-11l-10-1-11 1-10-1h-11-10-10-11-10-11-10l-10 1-11-1h-10-10-11-10l-11-1h-10l-10 1h-9-11-10l-10-1h-11-5l-10 1-10-1h-11-10-5l-5-2-3-5 10-2 10-1h11 10 10 10 11l10 1 10 1 11-1h9 10 10l10-1h11 11 10 11 10 11l10 1 10-1h10 10l11 1h10l11-1h10l11 1 10-1h10 11l10 1 10-1h10 10 11 10 10 12 10 10 10 11 10l11 1 10-1 10 1h10 11 10l11 1 10-1h9l-5 2-5 2-5 2-5 2-9 3-11-1h-10l-9-1-1 5 5 3v5h11l9 1 5-1 5 3 1 5v5l-11-1h-8l-3 4 2 6 1 5 10-3 5 1 4 2 4 4 1 5-11 1-1-10 2-10 4-9 3-10 2-10 3-10 1-6 2-5 10-3 10-1 10 1h11 10l10 1 11-1h10 11 10l11 1 10-1 10-1h12 10 11 10 10 11l10-1 10 1h11l10-2 10 1h10 11 10l10 1h10l10 1h10l10-1 11 1 9-1-11 1-10-1h-10-11-10-10-11l-10-1-10 1h-10-11-11-10l-11 1h-10-11l-13 1h-10-11-10-11l-10-1h-10-11-10-10-11l-10-1h-10-10l-11-1h-10l-10 1-10-1-11 1-11-1h-10l-10 1h-11-10-11-10-11-10-10-11-10l-10 1h-10l-10-1h-12-10-11l-11 1h-10-10-11-10-11-11-10l-11-1h-11-10-10-11l-10 1-11-1-10 1-11-1h-10l-10 1-10-1h-10-11-9-10-11-10-10-10-10-11-10-9-5l-4-3-2-5 10-2h10 11 11 10 10l11 1h10l10 1 11-1h9l10-1h10 10l10-1h11 10l11 1h10 10l10 1 11-1 10 1 11-1h10 11l10-1h12l10 1 11-1h10 10 10 11 10l10 1h11 10l10-1h11 10 11l10 1 11-1 10 1 11-1 10 1h11 10 11 10l10-1 10 2h11l10-1 10 1 11-1 10 1 10-1h10 11 10l10-1h10 11 11 10 10 11 10 10l10 1 11-1 12 1 11-1 12 1 10-1 10 1h10l10-1 11 1h10 11 10 10l10 1 5-1 5-2v-5-5l-10-1h-11-10-11-14l-10-1h-10-10l-10 1-11-1h-10-10-11l-11-1h-10l-12 2h-10-11-10-10-11-10-10-11-10-11-10-10l-10-1h-11-11-10-10l-10-1-11 1h-10l-10-1h-11l-10 1h-10-11-10-11l-10 1-11-1h-10-10-11-10l-10 1-11-1h-10l-10 1-10-1-11 1h-10-10-10l-10-1h-11-10-10-10-11-10-10-11l-10-1-11 2-10-1h-10-11-10-10l-10-1-11 1h-9-11l-10 1h-10l-10-1h-11-10l-10 1-11-1h-10l10-3 4-3 10-1h11 10 11 10l10 1h10 11 9l10 1h11l5-2 5-2 4-2h11l10 1h10l11 1 10-1 6 1-1-6-2-4-4-4-9-2h-11l-10 1 11 1 10 3 10 3 10 2 10 3 10 2 10 2 9 3h5 11 10l11 1h10 10l11 1h10l12-1h10l10-1h11 10 10 11 7l5-1 5-3 5-2h10 10l11 1h10 11 10 10 11l10-1h11l10-1 10 1 10-1h11 10 11l10 1 10-1h10l11 1h10l11-1h10 10l11 1h10 11 10 10 11 10l10-1 10 1h11 10 11 10 11 10 11 13 11 10 10l-10-3-10-2-11-1-10-2-10-3-10-1-11-1-5-1h-11-10l-11-1h-8l4-4 4-4 10-3h10l-9 4-11 3-10 3-9 3-10 4-9 5-10 4-9 4-10 3-10 5-9 4-9 4h-11l-10-1-12-1-10-2-10-2-10-2-10-1-10-2-10-1-10-3-10-1-10-1-12-2-11 1-10-1-11-2-10-3-6-4-2-6 10 5 9 4 9 4 10 3 10 3 10 4 10 2 12 3 10 2 10 2 11 2 10 2 10 2 11 2 9 3 10 2 10 2 11 2 10 2 9 5 5 3 9 4 10 1 11-1h10 11l10 1 10-1h10 11 10l10 1 12-1h10l11 1h10l11-1h10 11l11 1 1-5 1-10-1-10v-10l-1-9-3-4-5-2-4-3 1 11-1 11-1 11v10l1 10-2 5-3 3-5 2-2-10-2-10 1-10v-11l1-10-1-10-1-5-3-4-5-1-4 9v11 10l1 11v10l-1 10 2 5-4 3-5 2-5-3v-10l1-10-2-10-1-10v-11-5l-1-5-3-4-5-1-3 10v10l2 10-2 10v11l1 8-2 5-3 4-5 1 1-11v-10l-1-10v-10l-1-10v-10l-4-3-6-4-6-1-3 10 1 11 1 10 2 10 2 10-1 8 1 5-5 4-5 1v-10-10-10l-1-11 1-10-1-10 2-10 7 7v11l2 9 4 10-8 6-8 6-6 5-4 1-6 6-2-10 2-11v-10l1-10v-10l1-11-1-6-1-6-3-3-5-2-1 10-1 11v10l1 11-1 10-1 10 2 10 1 7-2 5-4 4-7 1-1-10v-10l2-10-2-10 1-11v-10-7l-5 1-5 4-5 4-1 10-1 10 1 11-1 10 1 8-3 5-3 4-2-10v-10l-1-10 1-10 1-11-1-6-1-5-3-4-5-1-6 1v10l2 10v10l-4 10 3 10 1 7-3 4-4 4-5 1-1-10 1-10-2-11-1-10 1-10v-6l-2-5-4-4-5-2v11l1 10-1 10-1 11-1 10 5 9 10 2 10 3 10 2 10 1 10 1h10l10-1h11l10-1 10 1 10-2h10 10 10 10l-6-8-11-2-10-1-10-2-11-1-10-1-10-1-12-2h-11-9v-10l-1-10-7-7-10-2-10-1-12-4-10-3-10-3h-5l-2 10-1 10 1 11-1 5-5-1-5-1v-11-10-11l-2-5-3-4-5-1-4 2v11l-1 10-2 10 1 5-2 5-4 3-5 1 1-10v-11l-1-10-1-6-1-5-5-3-5-1-2 10 1 11-2 10v6l2 5-3 4-6 2-6-1 3-10-1-10 1-10 1-8-1-5-4-4-5-1-4 10v10l-2 10 1 8 1 5-2 5-6 2-5-1 3-10v-10l-1-11v-8l-1-5-3-4-6-1-5 2-1 10-1 10 2 10v9 5l-2 5-5 1-7-1 3-11 2-10v-10-8l-1-5-2-4-7-2-4 2-2 11-1 10 2 10v10 9l-3 4-5 3-5 2-1-10v-11l1-10-1-10 1-9-1-5-3-4-5-2-3 10v10l-2 10 1 11v10l1 10 8-6 7-7 7-8 5-8 8-8 9-4h9l-2 10-2 10 10-1 11-1 10-2 10-3 10-1 9-4 10-3 7-3v11h-11l-10-2-10-2-11-2-9-1-10-2-11-1-10-2-11-3-10-1-11-2-10-1-9-2h-5v10l-2 10v10l1 11 1 11-1 10v10 10 11 10 5l-2-5-3-4-2-5-3-4-2-5v-11l1-10-1-10 2-10-2-10 1-11v-10l-3-10 1-6-2-5-4-4-3-4-4-4 2 10v10l-1 11v10 10 10l-1 10 4 4-5-2-5-2-5-2v-10l-2-10v-11l2-10-2-10v-10l1-5-5 3-3 4-3 4v11l-1 10-1 10v10l1 10-2 5 2 5-5 2h-5l1-11-1-10-1-10-1-10v-11l-2-6-1-5-3-4-5-1-1 10-1 10v11l1 10v10 6l-2 5-4 2h-5l-3-10 1-9v-11-11l-1-11 1-5-3-5-5-2-3 10v10l-2 10v10l1 10v6l-1 5-3 4-5 2h-5l3-10-1-10-1-10v-10l1-11v-5-5l-4-4-5-1-4 3-2 9v10 11 10l1 10 1 5-2 5-5 3-5-1v-10-10l1-11-1-10 1-10-1-5-4-3-3-4 1-5h-5l-2 10 1 11-1 10v10l-1 11v6l-1 5-3 4-5 2-2-10v-10-10-11l-1-10 1-5-2-5-4-3-5-1-2 10v11l1 10-2 10v10l1 8-1 5-3 4h-5l-2-10v-10l-1-11v-10-11-5l-2-5-4-3h-5l-2 10-1 10-2 10 1 11-1 10v5l-1 5-3 4-5 1v-10l1-11v-10-11-10-6l1-5-4-2-5-2h-5l-1 11v10 10l-2 11 1 10v6l-1 5-2 4-5 1-3-10 1-10-1-10-1-10v-11-6-5l-2-5-5-1-5-1 1 11v10l-1 10v11 10l-1 10v6l-2 5-2 4-2 5-3 4-2 5v-11-10l-1-10v-10-11l-1-10 1-10v-7l-1-5-4-3-5-1-2 10v10 10 11l-1 10-1 11 1 10v10l1 6-4-4-5-2-4-3v-10l1-10 1-11-2-10 2-10-2-10v-6l-1-5-3-4-5-1-3 10-1 10 1 11v10 10 10l-1 5-3-5-4-3-5-4-1-10 1-10-1-11v-10-11l1-5-4-3-5-2-5-2 1 10-1 10v11l1 10-2 10 1 11v5l-3 4-5 3v-11-10l-1-10 1-11-1-10 1-10-1-10-1-5-2-5-4-3-5 2-4 9v10l2 11v11 10l1 10-2 10v5 6l-5 2-5 1-1-10v-11l-1-10v-10-10-11-5l-5 2-5 1-4 10v10 10 11 10l-1 6-2 5-5 2-2-10 1-10-1-11v-10-11-10l-1-4-2-5-5-2-5 2-2 10 1 10v10l-1 10-1 11 1 10v5l-2 5-4 2-5-9v-10l1-11v-10-10-11l1-4-1-5-4-4-4-1-4 3-1 10v10 10 11l1 10-1 11 1 5-4 4-5 1-5-1 1-10v-11-10-11l1-10 1-9-2-5-3-4-4-2-5 2-1 10 1 10-1 10v11l-1 10v10l-1 5-3 4-5 1-3-10 1-11v-10l1-10v-10l1-10v-6l-4-3-4-2-5 1-2 10 1 10-1 11v10l-1 11-1 5-1 5-4 2h-5v-10-10l1-10-1-10v-11l-1-5-1-5-3-3-5-1-3 10v11l-1 10v10l-1 10v5l-3 4-5 3-4-10v-10-11-10-10l10-3 10-1 10-2 10-1h11l10-1 10-1h10 11 9l10-1 10-1h11l9-2 10-3 10-2 10-4 3-9 2-10-1-11-1-10v10l-9 5-10 2-8-6-5-9 1-10-2-10-1-10-4-9-9-5v-10l9-3 9-5 7-8-1-10-7-7 5-10 1-10-1-10-2-10-8-6-10 1-10-3-9-5-10 1-8-3 5-10 1-10 1-9-5-8-7-7-10 2-8 7-7 7-8-8-9-2-10 4-6-8-1-11 1-10v-10l8-6 8-7 8-5 8-7 9-6 8-5h11l9-1 10-1 10 2 11-1 10 1 10-1h11l10-1h10 10l10-1 10 1 11 1 10 2h10l10-2 9 5 10 2 9-3 10-3 5 8 3 10-2 10v10l-3 10 1 10h-11l-10 2h-10l-10 3-8 6-4 10v10l2 9-1 10-1 11 1 10 1 10-2 10-1 10 3 10 3 10-4 10-3 10-2 10-1 10 2 10v10l-7 8h-10l-10 3-7 7-5 9-9 5-10-1h-10l-3-10-3-10-4-9-4-10-1-10-4-11-3-4-1-6 5-2h5l2 10v10 11l-1 10 1 10-1-10v-11-10-10-10-10-11-10l1-11v-10l-1-10 1-11v-10-10l1-10v-11-10-10l-1-11v-10-11-10l1-10 1-5 4-3h5l1 10-1 10-1 10-1 11v10l-1 10 1 11v10l1 9v11l1 10-1 11v10l1 11-1 10v10 11 10 10 11 10 11 10 10l3 3 5 3 5 1 2-10-1-10v-10-10-11-10-11l1-10v-10-11-10-10-10-11-10-10l1-11-1-10v-10-10l-1-11 1-10v-10-10-5l3-4 5-1 5-1-1 10-1 10 1 11-1 11 1 10 1 10v10 11 10l-1 11 1 10-1 10 1 10v11l-1 10v10 10 10 11 10 10 10 11l1 10v5l3-3 4-4 3-4 1-11-1-11v-10l1-11v-11-10-10-10-11-10-10l1-10-1-11v-10-10l1-10-1-10v-11-10l-1-10-1-10 1-10v-5l2-5 5-2h5l1 10v10 11l-1 10v10 11 10 10l1 10v10 11 10 11l-1 11v10l1 10v10 10 10l-1 10 1 11-1 10 10 2 5-9-4-9-1-8v-5l4-5-2-10 1-10-1-11 1-10 2-10-1-11v-10-10l1-11v-10l-1-10 1-11-1-10v-10l-2-10 1-11-1-10-1-5 1-5 4-4 5-2 5 1 1 10-3 10 1 10-1 11v7l5 2 5-2 5-3 2-10v-10l-1-10 1-5 1-5 4-3h6v10l-1 11v10 8l1 5 3 4-2-5v-5-5l2-4 5-3 4-9-1-10-9 6-9 6-8 6-9 6-9 5-8 6-7 7-9 6-7 7-9 5-8 6-9 7-8 6-9 6-8 5-5 2-4 3-1-10v-10-10l1-10-1-11-1-11 1-10v-10-11l1-5-3-4-4-3-5-2v10 11l-1 10-1 10v11 10 11 10l1 10v10 5l-2 5-5 2h-5v-10-10l1-10-1-10v-11l1-10v-11l-1-10v-10-10l-1-5-1-5-5-3-5 1 1 11-1 10v10 10 10 11 10l-1 10 1 10-5-9-3-10-3-10-1-6v-11l1-10-1-11v-10-5l-1-5-3-4-5-1-5 10 1 11v10l1 10-1 10-2 4-5 2-5 1-1-10 1-11-1-10 1-7-6-1-4 4-5 2v10l2 11-1 10v5l-1 5-4-4-5-1-4-10v-10l1 12-1 5 11 2h10l5-1 10 1h11 9 10 11 10 11 11 10 11 10 10 10 11l10-1 9 1-3 5-2 4-3 4h-10l-11 2-10-1-10-1h-10l-11 1-10-1h-10-11-10-10-5l-5 1-2 5v5l10 2h10 10 11l10-1 10 1 11-1 10 1 10-1h11 10l10 1h5l3 4 2 5-9 4h-11-10l-10-2-10 1h-10l-10 1h-11-10-11l-10-1-10 1 5 1 5 2 5 1 5 2 5 1 6 1 4 1 5 2 10 2 10-1h10l10-1 10-1 11 1 11 1 5-1 4 3 3 4 2 5-10 1h-11-10l-11 1-10-1h-10-10-5l-5 2-4 3-1 5 10 2h11l10 1h10 11 10l10 1h5 5l3 5 1 5h-10-10-11l-10 1-10-1h-10-11-5l-5 1-3 4-1 5 9 4h10 11 10l11 1 10 2h10 5l3 6h-11-10-11-10l-10 1-10 1-5-1h-5l-4 4-1 5 2 5h10 11l10 1h10l11 1h10 10l-1 5-3 5-10 2h-10-10-11-10-10-11l-5 1 3 4 4 4 2 5 11-1h10l10 1h10 10 11 5l5 1 3 4 2 5-11-1-10 1-10-2h-10-11l-11 1h-10-6-5l-3 4-2 5 10 4h11l10 1 10-1 10 1 10 1h10l8-1-4 3-5 1-5 1-5 2-5 2-5 1-5 1h-11l-10-1h-10l3 4 6 2 4 3 5 2 5 2 7-7 4-10 2-10 2-10 3-10 2-12 2-10 2-10 2-10 2-10 4-9 1-10 3-10 3-10 2-10 3-10 2-10 3-11 2-10 3-10 2-7 10-4h10 10l10-2-10 2-11 1-10-1h-10l-11-1h-10l-10 1-10-2h-11l-10 1-10-1h-11l-10-1-10 1h-10l-11-1-10 1h-10-10l-10 1-10 1-10-2h-7l-5 1 5-2 3-4 5-4 11-2 10 1 10-1 11 1h9l10-1h11 11 10 11 10l10 1 10-1h10l11 1 10-1h10 11l10 1 11-2 11 1h10l5-1 4-2 2-5-9-4-10 2h-10l-11-1-11-1-10 1h-10l-10-1-10 1h-10l-10 1-10-1h-12-11l-11 1-10-1h-10-10l-10 1h-10-10-10-6l4-3 4-4 5-2 4-3 4-2 11-1h9 10l10 1 11-1 11 1h10 11 10l10-1 11 1h10 11l10-1h10 11 10l10-1h10l-4 9-7 7-9 6-8 7-9 5-8 7-8 5-8 7-8 6-8 6-5 9-2 11v10l1 10v11l1 10 1 11v10l1 10v11l1 10-2 10 1 10-2 10-1 10v10l-2 11-1 10v10 11 10 11l-1 10 2 10v10l11 3 10-2 10-2 11-2 10-1 10-1 10-2 10-2 10-1 11-2 10-1 10-3h10l10-1 11-1 10-1 10-1 10-2 10-1 11-2 10-1 10-2 10-1 10-1 10-2h11l10-2 9-4 3-10 3-10 2-10v-10-10l-1-10-6 8-7-8-3-10-3-9-2-10-3-10-2-10-8-8-10 1-10 2 1-10-2-10v-11-10-10-11-10l8-7 8-7 5-8 7-8 2-10-1-10v-10-10-11l1-10v-11-10l-1-10v-10l6-8 6-8 5 8h10l10-1 10-4 5-9v-10l6-8h10l6 8 8 5-7 8-4 9 1 10 5 9 9 5 2 10 6 8-10 2-10 4-6 8-1 10 3 11 8 6 9 4 6 9 1 10 2 10 6 8v10l1 10v10 10 11 10 11 10l-9 3-11 2-10 1-10-1-9 3-8 8-6 8 1 10 3 9-3 10v10l-1 10-10 3-2-10-1-10v-10-5-5l2-5 2-5 2-5v-10l-1-10 1-11v-10-10l-1-11 1-10v-11-10-11-11l1-10v-10-11-10-10l-1-10 1-11v-10-10-5l5-2 5-2 4 10-1 10v11 10l-1 11 1 10v10 10 11 10 11 10 11 10 11 10 10 11 8l5 1 5-3 3-9v-11-10-10-11l1-10-1-11v-10-10l1-10v-10-11l-1-10 1-10-1-10v-11l1-10v-10l-1-11 1-10 2 5 1 5 1 6 1 5 1 5 1 5 1 5 1 5-5 9-9 5-5 9v10l2 10 3 10 5 9 5-2h5l1-6 1 11-1 10v10 11 10 10 10l-1 11v10l-1 10v5l3 5v-5l1-5 2-4 4-4 1-10 1-10v-10l-1-11 1-10v-10-11-10l4 10 2 10 1 10v10 11 10l-1 11-6 8-10 4-10 4-9 4-10 4-8 5-9 6-3 9v-10-11-10-10-11-11l-1-10 1-10 1-10v-11-10-10l-1-11v-10-10l1-11v-10-10-10-10l-1-5-2-5-5-1-5 1-1 10v10 10 11 10 10 10 10l-1 11v11 10 11 10 10 11 10l1 11v10 10 11 10 5l-1-5-1-5-3-4-5-3-2-10v-10-11l1-10v-10-10-10l1-11-4 3-4 5-3 4-3 5-1 11v10 10l-1 11v10l10 3 11 1 10 2 9 4 3 10 1 11v11l-2 10-2 8 4 3 5-2 3-4v-6l-10 1-6-1h-5l-3-4-2-5v-6l10 1 5 1 2-5 2-5-9-3h-7l-3-5-2-5 10-3 10 1h10l7 1v-5-5l10-3h10l10 1 11-3h5l-10 1h-10l-11-1h-10l-10-1h-10-10-11l-10-1h-10-6-5l-4-3-2-5h11 10 11l10 1 10-1 11 1 10 1h10 11 10l10-1 6-1 4-2 2-5-1-4-10-2-11-1h-10-10-10l-11-1h-10-10l-11 1h-11l-10-1h-5l-4-3-2-5 11-3h10 10 11 10l11 1 10-1 10 1h10l11-1h10 5l4-3 3-4v-5h-11l-9-1h-11-10l-10-1-10-1-11 1h-10l-10-1h-10-10l2-4 4-3 11-2h10 10 10 10 11l10 1 10-1h10l5-2 5-2 2-5-10-3-10-1-11-1h-10-10-10l-11-1h-10-10l1-5 3-5 10-1 10 1h10l11 1 10 1 10 1 10-1-7-5h-10l-9-1h-5l-5-2-5-2-5-1-5-2-5-1 10-1 11 1h10 10 10 6l-4-3-4-4-4-4-4-3-11-2-10 1h-10-11-9-5l-4-4-1-5 10-1h10l11 1h10 10 5l3-4 2-5-2-5-10-1-10 1h-11l-10-1-8 1-5-2-4-3-1-5 10-4 10 1 10 1h11l10 1h5l3-5 4-4 4-3-10-4h-10l-11 1h-10-10-6l-5-1-4-3-1-6 10-2 10-1 10 1h12 10 9v-5l-3-4-2-5-11 1h-10l-10-1-11 1-3 10 1 10 1 10 2 11 2 10 2 10 4 9 3 6 10 2 11 1" stroke-linejoin="round" fill="none"/><use href="#d" x="29.54" y="25.92"/><use href="#c" x="-7.54" y="7.3"/></svg>'


def _png_per_platform() -> str:
    os = platform.system()
    match os:
        case "Windows":
            return "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"
        case "Darwin":
            return "iVBORw0KGgoAAAANSUhEUgAAAV4AAAC0BAMAAAAurVl5AAAAJFBMVEUAAAC62v9OluLe6fvt8/u62v+62v+62v+62v+62v+62v+62v9aaaNdAAAAAXRSTlMAQObYZgAABrNJREFUeNrt3c1r3EYUAHBh0xx8k2kxxZesHNKwvZhdmnvh0Q3jS0nwvcTG0FvtGkzP7cE9toXQTS/GnZOOrS/F/1w10kgrzZdmRjPSDN4HJnEivD8/P430ZmblJBkczy6qSEaK3aVJ8EfXXv5Y/94sy7642cSP/d5F9nJC7yxND1req5v2J8U3kx3tUuUFF8F50yJqbxq/t4yzrbfXu9p6PXpXLeJlBF64kcZlkN4VrKLyQlzeT0FaEVeb61var51g/BVENF5aJdN7sxutCMY7UzKvwcR73Pn0uwm8ZvWr8M5zedyVR+zI/2scb1Uee8WrFn+ovH9XXzQGLyq95X/G4MWReYF60fhe8u8dL+1NVV4M0OPl0Q7zy3wDzrwdsgvvOai9soCJvLIMa3vzkfN7bu1Fk3ghLm9s9WDrbcbfWLz0/sGdd3M/qfSe0w9jL/LmVd7/Av0w86LJvHb1QE83b/XbzFdz49k31ccgbz6i1278xdAeH/LIxocn7L3aevUDGO8qcG9u6L1M9xfTek37t7C8q1G92IX3OkyveP6MeFerkOuh09GT+pWvAZSRReUVrM/reM80+vn+cVfsvYZV753O6N76HpncE90Zzu9M5sUgym+4XjqFGZHXf367x+4NKwa7+VTD/J658ZIxIgLvfbaJ5w68r5VWcJlfu/szxvtM41wLyftyDC8M6jfH9+ZbrxNvNWPC/fwVXrKPqN5GsHLjrS4aJl5cuzW9aXd2T+59fXFx4cULZt6Dygt93p7kvs/ohlXjelAn2Jf3rC4Xk/ON3IL1JJjzpu1ZXn3v+6wbSysvbOYqh3kvD3q8Z/w2Wjtvk2Bs4uXmdsbz1qXs05skSzdeVJ1yFRsjX17hlnwbL3TGCgxhewFh0TJBwF52zgqAyXLQXnoz0QZ79Jbj8JHMCzre+tTbnHlDvN9/UHqXqv6YOZWqT3kvOQPBon6vsiZb1EAOH+AVZlZwZSvA9CrCejNR1N4f+PY0Xa/XlTbT2vmq9kryW0pxWQ7shJTo/U4L+TuISu96/YHP7rE4yz1eVC/Sy7fTkQQmA70kHHirHzfqbTuTYLxcfqE1iICgo5/UWyUYcTUA8hkIsZeS/vDtzfl6QOoZk+C8otGiz/vThF6Mzb1rnfDkzTedHD9Lma0HhCcvvWsQTVYnMydexTF6a0DC6wS49jaXb8UxH8295Xz1XLwgO8ib1rEelmAk6CV8eHXi41Py8k3c9F6IzCu5As8F7VPwXogov4gHh+2FToMcSf2GlV966yjz4uC8qvxiBCgmr/BCMo0Xa3qZmeCpvJhZJJTXL1R3a83JN423aSBwj5dMtd+1L86TeLm1TOV4Fom36QWSyb1cw4769mhs+s4sCm8r1n89CuO/yLz/COeFs9nnpeK3VBRcY0fmDfZky4N23iz78lEW//KPt1J6/7yt4tf6uzsSzj8M8e7OHh8tvL8Lc99417e3zSvs9RcEErAdeBfF8vvss1MS7wQTOcez21ao5newN2/n2J10P6Heb4U7y3W9uXz8Re68xS7EfSa/3XLR9+YBe6VV7ON8Y71fnZ76za9j7ydReU/fBuAtxvnDiLwvijd9hue9fx5XPdwlTrxNxOal6t1lm6jjRdwkCBrTuzD0FncOxTQIduGFkzG8xTYMhDEzDYW43i0JydsssKFqBoK5XYNctQdk5HoonwCyWRCs/oo0ewvGWyT44cSVtzELvBSIJ/ZyccR7ccsrHc9GqgcNbx6bN1d7IWgvokWM+MYuGC8We4EZ2MLxCnYjC8YIHe+DT++e2f2vzvUNIvM6r4fbn/W8gh1RPd7iOvFg6f3FxosV3nvh2yCdnW9g5UVy713icfwFeFOk+A0LfaXyYm7L5HheSWLVXvYKh/PRvOVE6isjL7liYMj1nt7oun8rw9QLT8j74qQeeE/8eOnrdLwI7L0AXx/69O6ybRHpMey9BvNnx2685JYScruHw4zn5d4UYOkl49HhY18M8GqsZxm4ySsu+r2EXC4ROfGiMbzHzrx5vvVuvTF6kcaTCHx5yQgXk7e1HmDmnage3mbmXsMQPNBmSP2+Y72bvsjh+ZZberN+L4Tk3e/3WtQD3nrpZqJ98jAK597cm7cQu/FCPF5s4+30SBre9sNJXHhz7WeKzcU93U6mimbA9nK+KRM61+tBJbH1xu3tVGEymVew7ZiLEka2NHZfcTwvPVXFv8GVD4mXSbdHr/I3zmp7h0W5B9Xcq/Ol5z2rsNbeZTvJ7rxegvWq+osQvcut10/sNA09Dd7r67X/B0eYm9TIBz4iAAAAAElFTkSuQmCC"
        case _:
            return "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"


def _events_for_map_test() -> list[Event]:
    """Events for map test."""
    return [
        PositionsEvent(
            positions=[
                Position(type=PositionType.DEEBOT, x=1477, y=-1296, a=0),
                Position(type=PositionType.CHARGER, x=-377, y=-365, a=44),
            ]
        ),
        MajorMapEvent(
            map_id="1132127808",
            values=[
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "2998807512",
                "360128560",
                "369397284",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "3559776670",
                "1727671436",
                "1921229554",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "4036787402",
                "1564564697",
                "1307495088",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "30638198",
                "487720185",
                "3165113179",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "3614459914",
                "376640576",
                "2782182568",
                "1295764014",
                "1295764014",
                "1295764014",
            ],
            requested=True,
        ),
        CachedMapInfoEvent(name="Erdgeschoss", active=True),
        MapTraceEvent(
            start=0,
            total=4739,
            data="XQAABADoAwAAAAAAAEINQkt4BmELocLzQwjmT1Njwlrk9CovzBCzC3LpPT3rXO6nYWr5WmICwI2TJGOldXPb4Ub5BHFynepTObhKC2Tox787y206axT1vhaD2/P7F4WVMw5lXOY9pltSNQgn76ILc0vnjKCyNxzKUj4B+WrweCmfcFDbpKYTYJygDSJEVxSCeHXrBVLYM31ExWSm7EPUeqMJYpXFTDbH/bWnYi8uQyrkb9Wm9lHXiEXbOg1CkXLxU+9VUP8vNgcHmxuDw+F8DWGxKFTzK76xrPp2z/dfKH+qkKejPEDA9lF9vALsBoxBum1zLbxbSEixaks0DpmntOxe5qIb/6JMwJBe6RHdsNBRGWYzIH3Oc14HctC74aUt3OI283x9lu8MeLakyV+GZoSExQ9mR4ZDJxCeFgkM+iaYAeXGo1+Nb1vUBLtYyUNreNOzjlI/0GMgLlhQFJgbIs4gCeK6LyshxR5wfCgLThzBwRoP7H5JXfzzP0nOjbG7nkJNmEGNzniRhRyjSVSM/73thyYnvQLsoowJGaNFw2vLZRhJuTJ/1g4XV7cSYQljCNKeY4xtlDMiunnsPAOkN4Xr1vbTCoaDmFxdpKnw3fEveVRiVoZ4A0RpRLTjfR1hilN31LbhyW4lTxCsAHaJyMmoRt7xX+bEZGhQjnGP1qh9M14z6HtDikodzSxODQ/qBW2xxTX0Ufi8NfoeM/vGVY0Y6lypoD5O2OYASCkmxalbb7oOnsHxePpiUDMrk4JPvWXbQU+hlPYs0r88f5J2Y8auzIeoReOke1met+Wigd8l85uRdaMRjFyEX9hHo7EBAc+K7o8=",
        ),
        MinorMapEvent(
            index=26,
            value="XQAABAAQJwAAAABv/f//o7f/Rz5IFXI5YVG4kijmo4YH+e7kHoLTL8U6OwczrMl+5Cn+j6EvprKUdquBVZgFpQToAHLTz2AlAA==",
        ),
        MapSetEvent(type=MapSetType.ROOMS, subsets=[5, 8, 10, 3, 4, 7, 9]),
        MapSubsetEvent(
            id=0,
            type=MapSetType.VIRTUAL_WALLS,
            coordinates="['12023', '1979', '12135', '-6720']",
            name=None,
        ),
        MapSubsetEvent(
            id=1,
            type=MapSetType.VIRTUAL_WALLS,
            coordinates="['2120', '-4581', '2106', '-6271']",
            name=None,
        ),
        MapTraceEvent(
            start=200,
            total=4739,
            data="XQAABADoAwAAACYAE0gB8D7Fr+Y1fhSFbwP2VgxT307ev0J0gP6ExAicwgr9TBNLiFjmrPlOXXvU11TaXYMsGp5XcHW8z0hvQSoOrlS6meLm4THCE5Qm2ufY103i+c+0KtXMwnL7wv3W1dTt1Q9EqIWHP1BU7gNhwY3u5yB0QHTHbLQoLSlzGgZrPKoFEWGTmy+uqF93TDug9mcUNPnVdU27lkB2vosDR5ArMALOpzgRrmzUwgDRCVsQpsbrHDT23P2y88AibK8RSSfW23PzSE6wXNrt3dmsLIhTVvsye/c3LrGOD2MNYFhKpEpL4IswcPbHKMR1dezFHHYC38TLIYrqlgUOK5H4OziGC5IYeJ6NMh3qmO1dcu+3MowYDnLpM9XlRKifnZrRxVo2gbtQeKvZZxTWBeOp5tUCfMffrdrXsAI+w1svaqvzYDRBvL/RszU6JlRoS6UGte7HYKbwhg2POKActTecQKKAiTxZvqVmBkiTvyQkgX/9bAF3l8V1t1hF8qY11TegAQmgExnMUYDf5t3oI0UgtsacA3OUjGnjdlMUcYTuiy9nlT9ku9nZoM+swz1SjlqISV2YJGN5cJxYxH2BUtj7Vbkv8I/g0g37cy1rKs7bRixIMyac61CkSmW7fgm4ajIQYE48oStouMg1KFApDVeyxlmZxp7NMYXNZt2sHr07E+6ZaTm+D+u2s5gnuTH9GnIRnMT5KOtAd6E59bTaNl0D8YeXxlMLxsWuQmsquDgAMGXnzumtOg==",
        ),
        MinorMapEvent(
            index=27,
            value="XQAABAAQJwAAAABv/f//o7f/Rz5IFXI5YVG4kijmo4YH+e7kHoLTL8U6OoLNmPkOR/iAKW494L6pU5z5weGz1LDuY+9sN12pb+fQQ6KxxRd6/vNOGnbZaGVn+xYVn7SJGugVyEhrIT8A62bQxjIeETOCqCkvFufRmAZauPeS6A1no+YyTf1GiP5t9QCqi8Zy9kyh/543wBWoL3qLjpSRH8YLZKsAezhwAW5oxW4A",
        ),
        MapSubsetEvent(
            id=5,
            type=MapSetType.ROOMS,
            coordinates="-1074,-474;-574,-474;-424,-624;-424,-674;-374,-724;-374,-1224;925,-1224;975,-1274;975,-1624;1025,-1574;1025,-1524;1075,-1474;1775,-1474;1775,-774;1825,-724;1875,-724;1925,-774;1925,-1174;2525,-1174;2525,175;2175,175;2125,225;2175,275;2325,275;2325,475;2225,475;2175,525;2225,575;2475,575;2475,675;2525,725;2575,675;2575,275;3425,275;3425,775;3175,775;3125,825;3125,875;3175,925;3425,925;3425,1925;3125,1925;3075,1975;3075,2125;2925,2125;2875,2175;2875,2475;1675,2475;1675,2175;1625,2125;1575,2175;1575,2525;425,2525;425,1875;375,1825;-1074,1825",
            name="Wohnzimmer",
        ),
        MapSubsetEvent(
            id=8,
            type=MapSetType.ROOMS,
            coordinates="-1274,-2874;-1174,-2874;-1174,-2824;-1124,-2774;1175,-2774;1225,-2824;3575,-2824;3625,-2874;3625,-2974;4175,-2974;4175,-2874;4225,-2824;6325,-2824;6375,-2874;6375,-2974;6375,-2924;6425,-2874;7175,-2874;7225,-2924;7225,-2974;7325,-2974;7275,-2974;7225,-2924;7225,-2874;7275,-2824;8375,-2824;8375,-1924;8425,-1874;8325,-1774;5675,-1774;5675,-1874;5625,-1924;4775,-1924;4725,-1874;4725,-1724;4675,-1724;4625,-1674;4625,-1374;4325,-1374;4275,-1324;4075,-1324;3975,-1224;3975,-1174;3925,-1174;3975,-1224;3925,-1274;3775,-1274;3775,-1624;3725,-1674;1825,-1674;1775,-1624;1775,-1524;1075,-1524;1075,-1574;925,-1724;-1274,-1724",
            name="Flur",
        ),
        MapSubsetEvent(
            id=10,
            type=MapSetType.ROOMS,
            coordinates="-1174,-4674;-874,-4674;-824,-4724;-824,-5724;2125,-5724;2125,-5575;2175,-5524;2825,-5524;2825,-4924;2575,-4924;2525,-4874;1625,-4874;1575,-4825;1575,-2924;1225,-2924;1175,-2874;1175,-2824;-1124,-2824;-1124,-2874;-1074,-2874;-1024,-2924;-1074,-2974;-1174,-2974;-1174,-3324;-874,-3324;-824,-3374;-824,-3424;-874,-3474;-1174,-3474",
            name="Küche",
        ),
        MapSubsetEvent(
            id=4,
            type=MapSetType.ROOMS,
            coordinates="3625,-1174;3875,-1174;3925,-1124;3975,-1124;4025,-1174;4025,-1224;4075,-1274;4275,-1274;4325,-1324;4625,-1324;4625,-1274;4675,-1224;4825,-1224;4825,-874;4875,-824;5075,-824;5075,-724;5125,-674;6675,-674;6675,-624;6725,-574;6975,-574;7025,-624;7025,-1074;7525,-1074;7525,-524;7325,-524;7275,-474;7275,-124;7075,-124;7025,-74;7025,-24;7075,25;7675,25;7675,225;7725,275;7925,275;7925,1325;7775,1325;7725,1375;7725,1475;7775,1525;7875,1525;7875,1775;6575,1775;6575,1475;6525,1425;6075,1425;6025,1475;6075,1525;6375,1525;6375,1975;6425,2025;6575,2025;6575,2375;6075,2375;6025,2425;6025,2625;5325,2625;5325,2525;5275,2475;4275,2475;4275,-174;4225,-224;3925,-224;3925,-524;3875,-574;3625,-574",
            name="Büro",
        ),
        MapSubsetEvent(
            id=7,
            type=MapSetType.ROOMS,
            coordinates="5075,-4474;5575,-4474;5625,-4524;5625,-6325;7325,-6325;7325,-4374;7375,-4325;7425,-4374;7425,-5974;8075,-5974;8075,-4274;7975,-4274;7925,-4224;7925,-3824;7575,-3824;7525,-3774;7525,-2974;7375,-2974;7325,-3024;7225,-3024;7175,-2974;7175,-2924;6425,-2924;6425,-2974;6375,-3024;6375,-3824;6325,-3874;6275,-3874;6225,-3824;6225,-3574;5075,-3574",
            name="Schlafzimmer",
        ),
        MapSubsetEvent(
            id=3,
            type=MapSetType.ROOMS,
            coordinates="3175,-4825;3425,-4825;3475,-4874;3475,-6075;3925,-6075;3975,-6124;3975,-6325;4525,-6325;4525,-6224;4575,-6174;4675,-6174;4675,-5325;4475,-5325;4425,-5274;4425,-5224;4475,-5174;4775,-5174;4775,-3574;4225,-3574;4175,-3524;4175,-3024;3625,-3024;3625,-3174;3575,-3224;3425,-3224;3425,-3474;3375,-3524;3325,-3524;3275,-3474;3275,-3324;3175,-3324",
            name="Badezimmer",
        ),
        MapSubsetEvent(
            id=9,
            type=MapSetType.ROOMS,
            coordinates="8375,-1774;8475,-1874;8425,-1924;8425,-2824;8475,-2824;8525,-2874;8525,-3124;9075,-3124;9125,-3174;9075,-3224;8525,-3224;8525,-4624;9125,-4624;9125,-4174;9175,-4124;9225,-4174;9225,-4774;9175,-4825;8525,-4825;8525,-5924;12075,-5924;12125,-5974;12125,-6075;12525,-6075;12525,-5924;12575,-5874;13875,-5874;13875,-5724;13925,-5674;14375,-5674;14425,-5724;14425,-5974;15375,-5974;15375,-5674;14975,-5674;14925,-5624;14925,-5374;14375,-5374;14325,-5325;14375,-5274;14825,-5274;14825,-4874;14075,-4874;14025,-4825;14025,-4774;13425,-4774;13375,-4724;13375,-4325;13425,-4274;13825,-4274;13825,-4024;13575,-4024;13525,-3974;13525,-3674;13575,-3624;13775,-3624;13775,-3424;13825,-3374;13925,-3374;13925,-2074;13525,-2074;13475,-2024;13475,-1824;13525,-1774;13975,-1774;14025,-1824;14025,-2624;14875,-2624;14875,-2524;14925,-2474;15275,-2474;15325,-2524;15325,-2674;16125,-2674;16125,-2524;16025,-2524;15975,-2474;15975,-1974;14475,-1974;14425,-1924;14425,-1674;14475,-1624;15325,-1624;15325,-1374;15075,-1374;15025,-1324;15075,-1274;15475,-1274;15475,-324;15175,-324;15125,-274;15125,-224;13525,-224;13475,-174;13525,-124;14725,-124;14725,-24;14775,25;15375,25;15375,325;14375,325;14325,375;14375,425;15125,425;15125,525;15175,575;15475,575;15475,1425;15225,1425;15175,1475;14725,1475;14675,1525;14675,1725;12675,1725;12675,925;12625,875;12575,875;12525,925;12525,1625;12125,1625;12125,675;12075,625;12025,625;11975,675;11975,1725;9225,1725;9225,1425;9175,1375;8875,1375;8825,1425;8825,1675;8525,1675;8525,-1724;8475,-1774",
            name="Wintergarten",
        ),
        MapTraceEvent(
            start=400,
            total=4739,
            data="XQAABADoAwAAAFT//LoAX2vNwroEQLzmnQtJ6t+EkvyFzO1+DHg/irN4w3ZO8zLJdslWe8QEx/yq4JQmEIpb9E/G88rYCed8NdW2KziFXiQKWmJLRBejBYCYFhw6tSuUIQMvZxJDanAH6Fv2TO+hBVOAnfHNVcM+yCeu4xPgQDAL98lugcGMnxUwXViikqRbaFiaDJGUtDMi3WhUGGo0yYjL1Hdh73uNoTtdnNjdLC+lGZlLyvKbXkRhhwsbG+EoXtiaXQRgL5WkeLS4PrRWBD9oEDYdmjhFjAKUNvvS7SBOIhFEjyn+832eaPjg86yPyvAj72kBDQQon7wd8+xyHr8CwjbHOZFLnPUt27nE3fWMrUQSUdn87nwrfrVyUV1RLsbZhwE0E6sbIdsHKDloxvfAKnfCNU3yNryGmhGtY2PIfPcp/ldd7IZgw7DhoXPNp/9609+FWsokILF0bL2/9N8XuQM9tuPqCt2H1uKfr00I75bl/SdVGNjmq0MfHM86MjXpNu3/BbQM3Zy9SbKsVlXTWskIk4Tng5iLACBOBFJ+KVWRASzP9iaT5vcRVY4xKMI56lLJBHc51Q/EUtGTx1Ln9ejkdCSyc/PoBI0nITSE/WW8/EpCSXG/HSvm7JC1Fs8dIoRbIbrdyKaYaO0NEjKGe31c3yfsYBFfgZ/7HicjC5qv6kwCya8ZztxakHTzci6TXH6dtB2X5LSN3kK1xqNhudL7+GU7qb+CJMN2kIw7hZ9fViVlTT3ID+HACYkRtLBrMDTb9RYe2390GW8sHBY2GA==",
        ),
        MinorMapEvent(
            index=28,
            value="XQAABAAQJwAAAABv/f//o7f/Rz5IFXI5YVG4kijmo4YH+e7kHoLTL8U6O/tP7Y2EYYVDkNYQ8LR1ByAxWv3mdF+TTjdYkU6qYd1k9vps4CYGibMeVCmQFUjplKR+PheFK+l5+yPnp9MA",
        ),
        MinorMapEvent(
            index=34,
            value="XQAABAAQJwAAAABugkgp5bzuDTsxgTfHTugMraGXP+ltaKAyC/YRb7guQlLvRsd2n53gBzbaSGj1F2zRCzVK4ZuJKsUKZc36xbnsfUnGC+A2Kcqjy81+BegacAibMi1Cigweb2tjnWTUkut51NJxB8n14PCo02RCfy3Z39PaElYt8PFdIcyDAA==",
        ),
        MapTraceEvent(
            start=600,
            total=4739,
            data="XQAABADoAwAAABSAT+QAgFQO2QqISbxzWjlNKH+CX3wUnNo7mcW1eHHbhNLLYQJ/57TDLDZ5miN5Up6Q8tNadb6toVK6s7DYNDslT25kjA91cxQOAkzNMpE9+4BxJC+gx+5z4tRGHX5YExg6UljXqFTVRqIYDULSRGria8DpcCKu+Xms7SWIw+EE6bVd/irNAb72DRltNX9Sl94pSQKpEuZz/of+iAm6jpaLHxhBZkb4+cjHuB+62gaCs0287+VgAqFLL8wxtHSC3O9ZS3StH7rp18z0jbEOjF6CHQCyD8IiDSMWZIar/hkIxUciLP7kcnnNYExR0o543mid/7dONjzYIeo5o/c2N7vm94NdTtKgFoKSmU6QXaRymVBwkRvrgt42/vDJ0Opf6aRUbY8ruhfSeJWs4b7w03lwAeEdNesAci7/9cuDhHyb+CivYYPoeVVQl19tQ6GDETdMe2s/98biKm8zNY3IwjngbclHBLN3/g2TJUuY3CuePRNPdHxAvpob4FTdZPsSUaCHI/LkBRHwWb5a7E+uFKhTkHi0gKXut2yCAvmgMOpOnHBHVRM9eiG/F2r/JP9gVnw0xpaW0e4HQ0e2v8SdbrPWu6v4yiCrJThLukrBWXTuZObEXWodVHyK6b61tiJfHfa1q6VOO/q3PA5QRli55Sa20ESNjPQ0dPGxiFwprYPJ5UpAsaOA1X46LCKbVcJZ/rr9yN/CXy9szhv5qpS6vwe7RpTMfOMN5AzB5EQBvrjeOdquaYfp+v4rcVojWEKZFcncyvZc8gA=",
        ),
        MinorMapEvent(
            index=35,
            value="XQAABAAQJwAAADfuMG3bzJl9/2wGCDArOSBeCsMQwsIdtJkf8Ko2AZGg4lT8xBGfsdqBjv7fAVfGNe3o5IsjH8MUTse1S9YAw03J4cnRmT+xva7YRC6RJz4glbjMiJRQQI3OGksS/bTVRwHEvWrSKX2MfYgjOTCcro4TYxvHUfrzYNpsMe6Yl8GHm47xsGVSU30lcYSxO9tEPI82/vSXmcWYnnu98Gc4AYK6P/8axwh4+MJC9UCIlWCC5noW2VYnzS/npxKUuPiYMHBXuaqpuzQyJ3YyfZPLQyvp7MmLLQJt/81lsH+YoL9ooSqhwVCsfwU5ItJJIJXnni9xbeeSn6TxrJ7FqRLPARw=",
        ),
        MinorMapEvent(
            index=36,
            value="XQAABAAQJwAAADVuIATZv7b3qYZ+EcqBeKoxiESZjVeBXbaP4M86YXV4mh7ZHA99IEA/aVt4HPe52di9JMR8vnrIwx0QM5Wbmsc9WzNL9DE1tFKDY0HopJI7tvrje5hr0HiWD5pnoq/DFyifTTPGuo33X8jz9Niz45E9ZjTp352TmrRpGl4nfrbcj52srts2AYIWBksNDxc91VyuYET4kSz+J4JJlHzkEG1erdbYVtoiXKI3PGcSsVg2",
        ),
        MapTraceEvent(
            start=800,
            total=4739,
            data="XQAABADoAwAAACIAENwAfMU+Zl3P7plKqfQitkzzy30GMkb2Te2tVVQIdKT0KoBuTYnQb0ij/Rjc87kMRhgLtghZ+jnbpjz3wtH4xyHRIYWOF2kS/MMpc62yq0/xFvlJg6NHbcxJysHYDpjEzSJU3GbaXR6cTrRzpfM7yfgr90JJYpsxlgbY4GJhJXkYpv7OsLtSPK66VWTNzV7acTYNFz+W8QW0vHlgYFSxra0ISBQ6pVgG5zthLmxu5UQvmJvBAxH2oAkwPig/vrvUoymYe7FR/xOMQa0QDUhUV7i5by6DxwurVdPqsPWHY2OHxyrdKlfMcjytqInLyZp7qBGIVvmCsBFXe2X3rtvLGZSG+wMySW0v294kxaLo3W9+kbbhfeDEAVK21Cj6MpJoxuWdOmbq6wkGmvxR2z9u0FPgcosF5PD5SVGHeKD5c07oP3IWpUrcs0oAZow4RnDEEbzQrdcnjjLUQc9dvBA9cW4LEGRMdG4LjA1+iE/zi+3lQFUaBKysM2BA9vxO9qeIrqM2HBPOc8Izkwm7B27ulZI98Gltzw7SdbOPK3Anzr9TNp6DB6kD6zpOnfilWk9zfBFDqI6e+pjDXhgIO9xWIL7/fRJgbWKaaRMODvMeBSj5DWX0mKJG19dF0GP3IugDuvoBtdKWz4dVmWa3zCOStULdT34AaIzbaQcamDED3YaUdjUwRhzSAQ35eEMVrhUDtRAEloYHHe1PpIApcZEb6MHACI1kvhZobNIXsdM88nQ236jy82XhamQBAA==",
        ),
        MinorMapEvent(
            index=42,
            value="XQAABAAQJwAAAABubEsjyjym4p3tetMqOx59dgIvptMvdoM4GxpnShdpXptVMLzFuYVDRf7/h/S7UPCRO4eeAoCtxihXhsGWRAB8T4dLkNtTamGpWIlWwDBygo7emXe1+tSSSFL7jgb728ddCkaFlPxBn4oNQBE3Q+QdC5k4gh3pgb314puwRhjXEtc952WgQ05xvj4E2tsyb5ksOKzj2ZsFMN0dZt/uUQmKeAE5mbkGHD+hzzb1z64jwvskvIYTWgpqgqyn6new0Cse+DxSAA==",
        ),
        MinorMapEvent(
            index=43,
            value="XQAABAAQJwAAAAJuJAACQ1SWRw8CS7i+oTNI/oRNIlOy3pTQnMs7S23RGiZ37I4JBRqPPB+zvngCz4KbPeIKiYrAIdGPOweVaXYyEuax3Sbl86zyXF6Ulb2D5xXQTMGOVXx+kowfklIuvL3ZqHG70n6AVGZ4ft+Xsya4HbknfHCF7J7Exc9MNSHfiaLMEnOfE5h5fRjz/zvXeRM3SSriB2p4f8cXbnfUAjt0fqWseq+wO2MmIk9B9v8YdVIAJ0XR3t2qXyQVvhHIrP316+kaCzoINKvQ0m7lozCJiuojuSRuJm5g4tLSJa9y5ycJ/uCNAsx0CnhE",
        ),
        MapTraceEvent(
            start=1000,
            total=4739,
            data="XQAABADoAwAAAGC/y2AAQwuK71Am43P130Yu8WZ48y6qAHPn7ZqZVIIulzOiDnCZnnnsvfwdCaLjaSH2x3UJlEeprtlh1Iql7WpY/DxD23SwFqSjVBw6EFwvzKr1Y3itNJxX0Ukioe78FotStM5ogjVhCQdqZBRxX6WacMV2HCXjIR5JkT8joKHyh9dc5CApRV+0eXpZia2mFdOANn03CLZSTEtHkqP+6oBATXoB5GFNS+OPmYPGSWeGn90Ij/Sy59WEgHx8uOsoElcUkLr8U/Tg1jkPiPPXD0y1Rtv1q+l4TvLED8aEouYZ4VWg9G0xi5CNcvcBCCMHUZFDp7Uc6GOw5paa268Kx0qDTj7iJNmKQEY22gBkK0oLu1ikcukyWMDUpAqUl2zuuCYR6xpuhqB1DJPBT/5i0/hYEHUz8+sINSbcf3L3aTkbxC+RqtkpASLCVq/qIiNBd/AaDf3cwKxkBvhsl+E4Qmub3p6VfwX/Oj2bzrIZl4SqCQLjiJwm+Ni2Ih3XHo1dR6y2bjkceyzVbxdEyRQTWAX9Iit9GdmHmlqbpXMTLF5smTy9vjc3nzOd9CiQR7ImYuZdzKufHIHwdAi1tnc64PezJ9kYA0ypbwJxTq7juOTsVWYr/Wc2RPvqA6JrZSsI/uQJqWw0qJGTTztmhYRZCD/kx0sXtDFIZGltkmrU8PdCwvdVKRWnpsaFBPy0EiujNa+slifpBAuCQxwH+Xd3/gy5BrSr/rZOW8zDEcZ9VT39qlJpA7Gf/Btopo8+TD4dmQ==",
        ),
        MinorMapEvent(
            index=44,
            value="XQAABAAQJwAAADTuOgQB/72wZx/w10vVxCJkURY5oE0S41Uc5f7JT6LYZ6fL04AwJBSq0587KyQUskSvz4T5UE1F6sA/FfNTZLwEDfTGKfG8wak9ReEY0SvWBj8PmjXJcgaqmIsfJror8V2ESV4I/1h/mQSRhL9n59VQ3tzDUES7BumIKlgIucZjahrna+TOiq3FQnv+ue5ZEM5vJZ5QIZ1h946uG7MrrAGOFGXC",
        ),
        MinorMapEvent(
            index=50,
            value="XQAABAAQJwAAAABudkoiWLJuOTk5RKILbyMBfP76HtHTCtvZ/YJNhEzK9NwMo87NlHgSUCJWpP/9Est/iTGHsSf9pBRbSFDN5oBWJxxWY/btgx8ANGHmAJZcvZ2dEclyro6MkCYu3L0uBe/7aDxjkWMZKQemJ1Q4QA==",
        ),
        MapTraceEvent(
            start=1200,
            total=4739,
            data="XQAABADoAwAAAHMAEl5If0S6ssowg4MubOYBDNEojGRhPSJfVOzMVWSve9WubGK+Y4A9p476wbLPrCQdBBJCCZEEZwS8OAlCagXvTDItzyPAUQAVdyEqy2FDWFQWRRkJXZK0kKKNJ5y5pybrUy4Mb0iUWssiPV4w/vi8kb+R5hahfR3iPjKmY6uvCsgonerzo4GgsS+pGpwWSBY6SVZahKM3Rvi6bDFmdBam1rIia4mAHTRYg/KIKtwISiC4eknE1RMGFoOpTKNl9aUMZp5dJZ4bFhkGP19rSwtk6vxSc7P/DrK5adQyfLApIcIDPW8BiTDQkiEwEHFiq1tWXHLcfCBJPkn4qHYgSIf24aKtSSTYzi5eqXNW4CZofC6rgP8/jQJz3ld2lexqwYRnGr0892gSLceNgUSsGazjvRJ8g8JOAegwgtju4Dy351BDkPQkWXTWiSEiKZw5VJaPzdkjtFmMxmstf5WKkuGFB7jzOODwdtke+LKUdOOeBdNGvqi2bNZ8xDTIV7l9RjlvlR+5Y2EggwMVkhNCVWt6OWmPAhCl8dz8SWIART+EIUgxLpEYTuKJmEDZqO59+AprAsaM+Jr9XsCYZg5cGPnCVAhWvH4BKJuB/6a+N+8gl3joJr3eyAfydPP2U28w7DlGbQncK0ujHdGhJsmtogyV5v4vJOZenqfj2E8MKbU=",
        ),
        MinorMapEvent(
            index=51,
            value="XQAABAAQJwAAADdt/gXVD01DCV/9DeewX+I2e4Oe5DwxyMDjkw983YgdhGbJX7VzgStunzm8//vTjuLSjPDxx8I7W8X8CaQ4XWq/snwo42YHIMPYJY4WDnMOvpzesXkhMCuXwXK9oGzTptDVrWXBRUCbsNRHvlMiglnrVb4DYZjdr/krvnpPscHHnNvhBt5Bbu7QWF/ESu5w3srpIMdpCmme07Sq2m39Aq5jvA9wPIhZD0vLamFnVIB9wSdero74BHVF16veKNTsh0zY9WfdB4qBcF+dKzIaTCyEK5EnY7rhtEsfOJx9auFm3loMQjt6yRYExRXww1Al0YEm4ikxG264AyaA6ifHUsAHBzNCv14qh9MeIjSJPZrtpClrKSJSs23SbKges6IoNzTGkOQ03c8/dCWKBfg6ChXA4nCP+PjMWjYGg3p4mfvSKwwuZpZTYsIUWvg+H48cM835AJXGpNIJ4HHLU8CgtqVuVEYjx7kqOmVpdYANoDDTPhV3+wFPdKilDYcts8ID3UPjfG5W7zHSqJBfrEn8pfmls5Vjt5xbbLfjWYAF7TIokrIoFsKBy1ZMDFYTvO24A09hzLr2ynXpoe+Q/wFVkkd3RvKD+EqoAm7Yerc/IlaM5nBncemiGX4wUX4+TT8A",
        ),
        MinorMapEvent(
            index=52,
            value="XQAABAAQJwAAADduHADckpSIU6Lc7gaVYbkAJ7nzivxyykJm7S5UENTnwWPpUkCxzMqUbZUSOVQynE7gXFy0B/peslyR7qCxAZQSixx4AIJgTKtHOHGEXPt5wHceFvpRYUj1Y2r2Ap7FZnNxd6gdrFj6BemyU8hHnIfgGjCPLKK8IPiDUuFDlsn0u1KjAMvgKlB/0idGrOcp6hstEh5qZBgQ8yG/iIVTpPjDhY9dbLb2z1NrdYuICNeslaume4uDY6p/yTvY/2G3wqE50maoBmTOFjlNz7Jtjp44dwNPT44nZ/n7kO3fQwA=",
        ),
        MapTraceEvent(
            start=1400,
            total=4739,
            data="XQAABADoAwAAACeABPNsLnS2XUX2wZx3t9P5x8w1Pdcv82IkyPvltnWdfU89fL9E98HxRC33HtCpBGHEPTNEtcSt/ETEuQHGLTJDiqNpdBF41VXt602b8fjtK+IpdkXc5fj2q5lUwffMJ8yILNGk6TthibuKq3ALDoloI4GxOlzOSwHU2lAaK3YKFP8YHJ6zPT7qUZgo9fXv2wlwS4M6j+FY8Daf9PRvwnmP6A3wFFaTuAJUVlelW5MKF7lsR1v2DI+WLWWmgjKWoueurGBwbKt5Q5/Bc31WdT2IBOCDVHJAk16i1NoRMzLsOkz9yamy7/4/vTX+GWibpKWdFFnemIVNd+0oxllo3Jz+l7Xc3FzDXYSZvHTfWjCVN6i0jz5deXkYQ1WKPYe/cpDykZNi/myqEzGsmkGEezdlmrhyyAMwPyEnjRnXaHXERkthX+Jy6CocxfaM0epk/hRlPIczRa8wH9wRLRMjpUyN0rlMJf9JWQAQgPTVhiFWclP44Fv57POkjOyia/VHfcdeZULHLMZyBFoAzsR990bzNm34LSySSoCJ561FTlJNzH8si6GR1n3ifKYvFIyV0hwHI/uiIE79izJaA7N57UmKfKXI8H5rTAGBHb+aOdxS6+BcadpcwDBjTzLITEWQoQzx3CHWWA22XcAtUZVYfq2rPGH0zK2jlA8ujUqYyBEyF2PiCD7SEAex9TOyOvYlTSIvv7dYzbCI9TPnI01vBfZU55E9gFq2q0i6ej1/OXPrmybV4TzVjf55BKaHryVYejrhHMLipyyGeGAV+RRUfOgWkJwSq5I8jK1nXDS2IPIEFlRe42ISweSJxlW/6g==",
        ),
        MinorMapEvent(
            index=58,
            value="XQAABAAQJwAAAABueEhRYy/zcKOyJula+ms1kF6/s3HLunhYjJwX3JUQ0S4YWBPnRSjIfE3XhUM/SCd3HJoe72si",
        ),
        MinorMapEvent(
            index=59,
            value="XQAABAAQJwAAAABuPElBZUtUurqaYu0MeEeAil4++JRw2vImdzqzdC/RlvGuG6OzaK3Xuy5nIu1m+tUotWkHqnR3Fx3UnAFgYtDFmfCCLNpG3jndVAbv3p7ZKCcacQA=",
        ),
        MapTraceEvent(
            start=1600,
            total=4739,
            data="XQAABADoAwAAACT//N/IZdU9vqFeSZYXx9dD03iTtRKrCeSq2QWQeIO3UB9g5fg8/cTzNYS9fDMLZLSCj+vw4/Gk2u9mgn0iwqzQmH33O8B1iaI140q8I6SSWIIKLpA8uEpiuGdGEb1fK0SXYc+mfOX2NansQvyKBB2/gyH6kSgR7XaG7+P+J/sAt/IZ9g/Xlxs7ARIMBBgtKR0JKExhYsv62QSJCQB/A1Yr5vGIUNy0xmhDuQu6Dbb9Xj3v6pOAdmwuGH6bj52z1z2BHgqV0Jme61EF1LkypVG6rqPaLe7yNqjRL1kJW9h/15/RmFqUnXCA9mI1kmvOv8/efqqZyf1SH78Zyev0sHtCpWTXC8no6NtrbgbZOMD6zGk7iy8Y7LjLbZmhWvprhOXzVt16f6Z3HPsWty9tTLoeUKevWBZFYJ1wbf5YwsYZqFLI2psUylfSlF9/sFhd0iYCCMIpS0Jp/4z2L6cMHYLuYjIhzqIiyzbHGKr57Yihe2uFF2NZ0+onJJKwHxqkmPrrarstdSRu4MJDtGEYdE+JGvh4/kCcL5UE3snc3H3DgewFofA3lVD0AE3LhXScP84nfHsgwiEYjsyCQ6RmkR11HDT6LnN1U/yDRqNlr/onVTjSVHajjsVOBK3p9PKmouk8wtkjIcRUOUEDy3BBkwut0d5BbTmrDq1U7N1DRpTe3T8YVXGmWUtZAXUG9eGCgcBf+E5AXGGxIC1XVOcXoQtEobfBr/gK2aFAYeckDYPDgZPLISQ/L+OqKruvPOW1AehUYCht0C0=",
        ),
        MinorMapEvent(
            index=60,
            value="XQAABAAQJwAAADcBXQeAAHimLPzHwr4JpEB5N7g5Lk+Dg/WqdIeFBDEA0yVh4AgSu169o8v2gNILCNK85c9hT2/ETMWSbq1CxPOqitsPIFQNsni7AA==",
        ),
        MapTraceEvent(
            start=1800,
            total=4739,
            data="XQAABADoAwAAADuADaZywW8As/oBlmkB11D+UPOuAHdTsZ3B8clwt2bcaVswjpi5G52FGS0Dui/7WuT4yp+A5VnFxhAKjEuoWDKxWSkaejiIw8dbmveIVLAr/z6eNp6atARmvVUw127SdrQkSssjlj61S10TsNciR4l5K7rp/jv+SgSHPpk1NJMat74pffUxjdmOWldkEjLeIXuUrJXP224scwfSqJSWPDkGhittT2qRwZL8RhgemHgvZ+PX9qXp2I2iH0CiR2Fjg1Xtc7chUpOZv9hYt9+aBMtPZdryJ0ocMqJ3tmatsgMtsdV0BnxpDyRwJcqYwUQcE9/LRWANWHg7pzbx7LLn5C34fn0zpyjHc2NaJ/oyNkS977K1vRqDw2JCtlzsB/fQbaSrcIJJeuBl6wbgwrtce6SnWo9QagVw8J0q3DV0s1VQ9b9Lz+cFyw+7Z2v6b+KsOi+RPG3XG+H2+0+fxSPMWJZUpuNm/8/LwjWLHtBPyzlIg19E/lEler6BJBlzmxYTu77o/mYJLC8p92jSujxYT9ZHYB9WWt/lKGBAT34miw5YgHb8fCzkJo+9HkDTaTMBuBTb71ovxqFP6vhzKefEhOPVMa8OufrDIic2vFsTvw5YXjAeJ4hGGSqM+NYHktFSHkpQ/l4jLEB5R2iDvYDSzeKimvzmIELj5JqZboC0S5F7UuQYRFBCQIoGFK/BQXE+/Hra+aav9B+d2+h4PdH79/ATghhACjzwbxZ3YhAkjMmM18hmoFIRPWo=",
        ),
        MapTraceEvent(
            start=2000,
            total=4739,
            data="XQAABADoAwAAACiARA7xKOpXh9w6tRV/962X4AXM7KEoJWSZYUUFgM4TbOom4ZOmIuNCVyZ5NCHl33WVqTkckmbLWT/00NIMPElrWAEfyyPAwGaZqxMq5EPBUbcfFbYl0tzV4rPEWQuHl4ME+YOtOhjLHo7pYPN2vbVQEzcHvh6XwbKuA3cJ5Z40XNfVGxwA7UHEFBfV5jBSVdM4dWhZa+mEghHPb4XGagUpJZhPpAWWR1C6B5Q1PaAA+Ddp70tB9hqh9OMCA1/Wq/TyaIwQhb+j0BhtoL0JHdGn37aTQZ9pwoVW7DONXlQzBoXaQe3dQOOrAw1NMP+hfj2J1JBU6uBXWGalgf374/xeGdEI8Tj2q2dlb4gdGsfgUeJGGSq1fMz8fkEXN5K4GWgxR7VQyAaOsBP7kccu+efuamSzriTaadPOYdGR7L7R8yphLFCMTvfgXiGjAjoXsICPOoa13bUpGONiVmlXOIgKnOQFKg3E9TqlEKJMYZCME64UFpWbKrD6hp5Y8j/Khe2saj3hrYd8AgQxLOz8oMBouJ+Qv6iV8+J8cwXhpzRlmqSSvSNIKCECfNdDvMr4L+k6+iHsDrRsKlwxBJaI4q4GogLCLdennX38hxqHPAQQyOtytHopd1+k2AcgXzsi3K3cX8uBPQZdQsSml9Cw61tavdjSjMhoSB8W7Xt888GaPZyXAA==",
        ),
        MapTraceEvent(
            start=2200,
            total=4739,
            data="XQAABADoAwAAAHSAgMhwztkS+/sUwQeeU+yxxnKuxKi4QpZwFsSQmIH+fZ3AfvjTIOLIaYPpkLRS3vLaAF3EVEBWg/dOumpWaHSmC4ns3tcGM72pwk5Z9W4GvJ6EMXocUBX+pxru2h3i10+vl479URY9fLmgzPYxYSerYVzYUzYTNKlAr+b5VPIL5Y/cfZ/51cwDflG4GrVlcn5bCEa7vsozaLzlSicyBwIkr92HtyDuiI0FeH07MI3hjNJTsxuPeT4HV4cErHSub6249ljTUUbuPDyK4d5MnZyQQECQ4vJeepzGkLDbvXB9r15iO1cLJTPdBD3PJtIaDpuoswk93JIUdehJMoFaggDWnLtvpEGp8gzneFot921sE8dpfIiHcXEAijev+gjfmzTHek6ISG7iOYfOlzL7+EzbAEU9dj874mTwwIaLEFJjzSFuFmzQZJBA9/S81DMKdX3eI1/HduD9ujFKK2g7+LV2hRxpkhRh5JAVdBj2ZgoZwt0Xf1draRgPt0Bn9v+YIzDNvksSAyPtuToS0ctkKcMUeIzYqYMP4kOhbA==",
        ),
        MapTraceEvent(
            start=2400,
            total=4739,
            data="XQAABADoAwAAACyAfe91Pq+r/Dh5CD8VsGd8dbH1zwm5kOblw18/by2wMlizbkCaC4bXVVVOK7+K+k6o80pRd4CBZ3eTtMXjuufKS+MBX7KrJq6o9BBoeQlidyJkuUuETTCUPRW6uizLnIv9GKU+Mb3DfArCMxKFpgqFJ0KUV8U4OAXLwrQm41anwpn2qAVTILILaaXo5ooWg+Pb9JvoAEDja1m94mChobxAtssK09yY3dkwY1fnOoV0v5DO1QNpSbhh++PPIWs6zdLm0clXWFGr381j7pbsXsGwpcQpSE2+02rtRxTVgjygz9/zZJdfKFgfM7etA+z+Ni4aKx3P2fNyxOYeIaO59Qsclj45wZToUHrI80091MZvFtwJtYp5cwG4OgSjujbaNcjiZHhugGc8gQtR+hhvPMKA9wLwREMSgtPpZwz4zPdjsDMIUkBT4uSFXlguNVRy7oHFTPYNgbE/vyjtYJnaaEIlN1kH4smHV++37FtvRipuMIZ4HZxTTHJDhiCVT5Kr0MKMfMQHjIWRjVfR4YIvCQuG5vzyl+TOPeaSbbteCh4GP7imlADTEXGNdcMMCk45fU8cWY0XfCoEmgUDDCrpyAGpJSck7nxoF3MNeWZxtVO8EbkRKF9L6FuEvw9JvosyeG4JJvwXxJiKXMKmMd4OZQtHhvLh00SNSDfdAs7msuohAdVQ+jNoXMJgnDYTiu24OQ==",
        ),
        MapTraceEvent(
            start=2600,
            total=4739,
            data="XQAABADoAwAAAAMAj7doM+KAaNXWbt7UpPlHlLh70MylOnzcyVEBu5J5jkKoYKm1xZreFXjeBcdIvmJ6cNH3VgOiTSuusOnClu0r5Y7wr54Nba5nJUcLNsiqb5ClLQsZOm45w8rdG0ucpq+FOMgNUR/TRoT9SIJWRcpQnG+BJZSU4+IjxXdCnhSrDf+15YQCfUniHQ7NINoi03sP7JRedfHzFby32oZNCdxjvnhfZEn/f4zT+k3YwcaC9Q5irzb9VIxm0WQQ/pHO+GrOPTpztRkmG7U/J8uidR6kmOuxqrGpPokS3lAHOt8SvWYS5Td+fKGtYTE6yAe0jlGHDa9UojgAoJOhWtf92+JzT+X4kV6lzhxm9gjcyYTPb0qcPzyhnjmJmE2FFFomA1F/P3o74WRKElLWhNdNkgcFrqYGiuYwbtLBjZ5NXBdxdv0O7E+gZOl+KnpCdR4McdDORx1tHeHwfxW0EGZUKwlaeOnJucy0Afw2OWQJ0vmnlGz35FEPvUv0UfyHzsTD8bbBOu4KtRY+Oig912pHyALkTpHOcsPwjYTQbCxzs8tZ2wSiQTErlo2fYNY/FHiRuTOhvizTym8W0CTOdkUwBMScnR5HnzTqXSaV/zQNlLmqfuE4SKTBgf0u+gENX2gowFBlqvc4IOvxzA1jucigCESdEjmwq95xlUgDxvkQXmJttr5dCKM2QkXS4xg6l8HuLgabJDP+1MDaukxY+jwjkSER6sriqMl1voEsqnv3gKxLjsFxSB+tYxueDzZRdwpHYHo6cJwIX5/LD2/6OgjHEv3UkpNbqhtqotIyb1QkZucvizdyswA=",
        ),
        MapTraceEvent(
            start=2800,
            total=4739,
            data="XQAABADoAwAAAC6AgU6cR4qDJz3RxK0kXJTqJ/nP0e+yBNe/36uAPDV9k8HoJYTAerk7RYO5F0Xm8PtC5HuXm8GSsF3y8fHrfUrMBozo0+y065ReEC4tImniW1Iu5v2+wacefdCqtCj4j6rvMb4C8QHnGTPwPMhO+9tDS42mZfPWWCxKonVfqBZxfhqpOp40Q30g25f07DId7qGkX4eS9nl+rsS3OJ5btqCgz1t7cIVbm+1K/MS5hUVbTK6I7AnMmUS9JIdn8kGLrLqV2WpcvpSAriN9mn3+OoZLWVDGpGsVIIers+MxPkFcr2oFdCBnctpVpx9KxjSlbwKM1XfZysz4+i5ttukVlo6otFpjPT2anGe6AEMw2xe88G32DaQJ591RmNK6o8KzJ+opn2OtoFiLgrUQ3dbGRaMBgtgWC2R39QoZ3rEpaCC/azbMP0Wku337enQyE8rA+d7Da6RR8azSqw68Z4huiieE3U9hz4zRY86yTZpvBokyXhv+boRf7BatBiXDrdkhHB95U1UlGPtCrRvcKUzJf3BE2GwvVXPSoQmUPdd/6ysMNHcgUW9e0NuIfdsjSgdeTh7glEBUy8ns3qtO/8fXDtqcjh2RVmntWGZlwY8QsPC9FW9TqKi1XIQYsAraXVux2TLy0i9cBeVBlGYxPa96nty8rcE++QlxjdcbEyc/qyEVTQaZ3Me6TjoAg9Aja2EEwXlOAv86Gr7O9L7e+xlHW9yFAe/sotATldKF8zo7SWSxgpXKnBytvg0IGnqO0rHadjeGlAEZfuxoeSDtMwwzhyGuw8F67Cb1smvitCokoHn85Tiq++wpLFTSXNIwJ0RCwlFLvd8EXVsA",
        ),
        MapTraceEvent(
            start=3000,
            total=4739,
            data="XQAABADoAwAAAEkAPKpxfXap/xBapiyOHws9nLMEqUj9mdV+Kd5qUam2KgIUojCz2UNUKJIcTEGY0H+5K8Q7XKsq2aus9UjER3WZKLvC1KpLceDXecA2+EAbo1QTIeTXZbSGj7Rk4Ru2INBVrwDkVD2p2/00F4rtcxxGCqSfU6Go4oxeG36qwJ9khqHufDlwWwW6zbXhkF2l0cWyZlwEWaer6jpTMsz1KwwqPA/i1g7DLdlgXhyNU2SJE1pIUyd+ddc8/Ij22ow/hcCebD/DGtaDlJJqvZ/jFjWnDYgMJqLTThthI7HbwS7fr0k1zKjE6XenaYLpsdWzxZ1zPP40RdnWiE0Zs7Oz7nBI+zKgKFra35ei5MCs03p5deIZ5PeFKBxvCKZYr2kEzfdBL+zaViChuKSewmIXnXavjkSe7rYrsrBs+2fnCL9fyMDR46vQYDpnzGTJDNYqR3OJ0pmXU+IgD5xJkderva8BgSYf/Y3hlc+e+gCj5xuhO64VnPMJjFIS0fnoZrkEp3jjkaEPdR4AW+EBVyEu59PH2xlR7yu7PWNuVP4v5VtnjYfa4lBrIhRGMc70q++eAE2oYG9IiTD+weKgningkefhGOien8ieS40aSmA+y122YdQUGksAEAAe8FPNxvo1BN19OZb/vgYx4JAxo9yb4rSgSWCiy4h7mFfeiajqJc6q+2OW7E8I9dLGdIFO0PlEr+H3jiLvAOLGSHj08gZD4dxAhdBmtT1hW1DHkNQZhxflGJ9HIYjEBhILEfjXOwA06qWpawA=",
        ),
        MapTraceEvent(
            start=3200,
            total=4739,
            data="XQAABADoAwAAAEaAAWNwwjUHjfU2jDlLQj0uZSSbXdZdssPevhGzmgPjxsivnu6BYhDOxi0BvtI7AdLuP6Iq+uCw/5m0/f2oroOD2eVIQUP9DQjQmC+T/6GQwyhZkr1vei3AsfaMRIyyHyXgUpnyLWATSU+AnHxToAaKxf7ZpjOz7hx1sNtB8GVpBiSeLOnaYsS0G4uESc5YsPrRO7LcomGVGY4mkYnHq1XLqFtzobXrEAs4MuwKitA0cVodBtALbVgAqdYO3HzNC0JkgmxpUb2A0IpfHRp3nNhtUKVTXmbz7W0r0Zih/3elYF5JVbi/XSvkazM/Zhs35dYDedb1ulNN0TIEn6SfjV67C3wGBmlltqH5QKuf3XmIXxLGtq8r4AYrFrT4OAbRY9JR8KyrgWa1IwavJ+Xz7ch2r5X8/QlpeOQ3Q8XG2wxCPPmUzVgyYzbNSG0nbQYXk2XRYwJFohSGrjTnwh73AZiawQ93LPC6+RZE5QtsIuH2+sSjgQGCJsy79hBAuE+PnAYQaATGv/znEA226OJFjNr/2QkVSFm6gRQJ1pJmTer4YDO3rMDhCuSJ98H8NhJq80TheHVUhktm2JvZ3IKNH4e0hTaRHUvFhZU0oVzQ+NBVDdas9APRSkWBMhfuvzxqpNCldiI3pKTVZ/vTIGYkqOqtYx2Lzd7y2G00pz2O16WaFOmMFwDCOGLq47puY0LazE/ha3Iw+JZEeh8yLoFRDpX3/QQvQk2Q3lbPaffgcObJW+95WfPB4KzcbQDCQWpxF6/b8sTEFIqBeFpUnVz8I/DEx1Y0KwA=",
        ),
        MapTraceEvent(
            start=3400,
            total=4739,
            data="XQAABADoAwAAABqAG7JjLm9/ZG46gP4hG6A5/8B4p/bXl7E2MEbwer/OBUEcrN6OKtXdNBpDMKS8YTAOs4d+EtDFgMlDaZEcThcukXpSW0vNubcz/UuV1onHV0cJkboriXTwh4ndjpUXu57ZSsDc8ilrTgglbe+UBlZtxJ6Ztefr0gm/Jz1fbpUc1EmK0kDBU8sB6BDeoJXkpH9ll8sk/oShUdZAatG3tg9lJ6p9OeLAlxvk1xYwHN4oIq/s9orwkH/R5+JCKOYW0TLoRfABgATu2W3rJgjTyZJz9tD35XPqSV89GwCuy1NkN4jS1NygyobqwhblX/oa3gGT/b27M/HTysgh0kmNwzr48sAfea2149m5QQJYp5WTNvDL+EOJ1MLgnYtRJZw+ahjpFP9S+ndPx7v0gzyFvX3qHxxGF1pXj/0O3THIXVtwgmdB4SrcrNeKVsPZAEJp8TzlFuyQlSv8eXKOsuXnrqUxsxp9oJ8CIw/4voudQ87WoFL78Sb24UpMYoF0y2sOtjUPZfx/zO9cJENYKJgUXvvWkVsg8XhaJnQFAoZlW44iEDYrvCAjDPmmT8PQpOs5YrzM8wkozD891guj89W8uWqA2Fyx+l52dN9ffFh28ufs6XXggQeK2lpPEdYhc2C2sZ/weotMKgkBq87G1R/4q7MMa/9vO/IcqBAh0yEnHALSoca5I1kSjhRgzRO9wNzkvCzhFX4o10Frq0sccJWYZ6lJVQZsFfLUWhPFOFbw9lfJMVicUuobk+CpI3MTVM4DMqSCw9H+VZo0c00z1Khax6Yqnq8A",
        ),
        MapTraceEvent(
            start=3600,
            total=4739,
            data="XQAABADoAwAAACqAGtlRwe/zwKkal1hNtl2teyhkF00CALfRnaGAuS9/OJmoy+0/0lxqQUZAT/9jFxpuOScm/03kUwELq2xILjWp3N+iCl8Ng8IQei4v9et6sbhnHZGphSa8Z9ZGkXYrykVM7rnVOKtKet1/buPB8lOadjcQDmrVTEhSN6W56q3HmF/ebWEmP91fwRrkMVq7RZpCglys7Bxrnn5FEhiQ+NgSNkN01ahORObp5e2EovhgbD/J4putrzZU4lqPEHXg7hZzLjTJi+nGzw8g1G7WwjnKtIr47J7kir9E+YnZYYVXWNCHXAZHoGURzNYhfE+O64FJjkmCQUgnBOKAF/pz/ZWgDNlTw/Z8LwddUuVgFddNM5nRUTxqwagnTxZIUhEgZAEh37pOYTZGLCL5TLYsCGA4x6ZMaEjGkP5xTJPwqgsV7yQWRy2ETJCY6IJjarcWdckGId813mvukGpH4FLk6HrzBix6AzXhyOdYKMbpNgloI4oQOFHawCfWtxrY3t7Dvid1wHkkeuil+juQAGUgauLl831l7Ws+stGiHoL2v7Q+R1yWI/29sZ7Nt5T3QZuz7XNZ3PD3TYyc9+7s1UuJZDelDF31WcSng///QKIB9aC/g8QR9dbG29RbXwj2coEDz7Bbz2qVD/o02wNltNLW02kR4WUSYdjuMMjtdh/gaT2JCDP2O73hu32qeJLKfbccrTj2B/Jmf0r13SxsbmahXPhoW5YZlMNJ2y9sh2ZrcaxwEWahA0N/LaYgNC9RBv4VYgA=",
        ),
        MapTraceEvent(
            start=3800,
            total=4739,
            data="XQAABADoAwAAAAV//HTdUuzE6litCrf8schzCGNAJYJycY7ZEcJhmgr2Ialj1Rm5ImKIrNjZfS/hon4H3nAaV4MFR0vB94iE8/pg6+1P+WnBl5ffU6feNCD9ZsnN8hoitYYXhXOGgoUpXwdmgL60wkoZ7WSTgUnvEQB0UcVl5dMynOcFYkwj4WhPYlYU3c3Oe/rFo2L5AOfYDv8bHMVjSBYKHoOpNL7b+DOJwrS/G5P5WIgj03+BNbH12v2CoDt8IKtTwedmkTyUu2X5/lZGw1MhXunoIHbYPHT0GZFF1r0NE90KuJf4PUOpjECoZ4IjbwyPvC3RcmWkvpxsNCmMjj5Pj/3y1/jRN1cZX6sUlvDJwxy6GkAgnM5sHZx8yid2ArVq7wLogpQw7iwtSLvI6emzt84/00RcME1RQjfiAdNRA1McUUnJugEmQgPcJgDkCquEtJ6sPQpmQwkXbt1FzTniCSXgNBCAxVO7KZ7YVZ/mT3DA/7G3PcJDT04QBA0frOfmvvrcwHKj1PLaeZ06a3tbUl2Kf/6W3D+nMPok7hdChCRh5zLiLF87sGJEHGtk0x0y9sDPlabeBFLXhKy/+dnjYqISUU3r/whMQeOEK36eUSXAkZkZ3GJ5OzGglyTSsEiiCmWDIzX/wULcDf45SVpB+KIoS9Sad9Et9TVjTW2Ou9dWyk2rrjbvlRQUyHnJGEfIHsjWshWhS59ycXhbsbm218UvQpS2TaJLQTYF8U84/N2pIFbt",
        ),
        MapTraceEvent(
            start=4000,
            total=4739,
            data="XQAABADoAwAAACIAEgJhQTEi1WOLx+qywvu0oPpS3shx2ap98o9qfiwObRjMPrNJ59PySJGQlopSxkwpPoluSlSNPJW1r9YlNDBFu0Fy4eTdUWnRD047yzXfRlUYjKWkHbU95bwD9p6HkBNSx91CeJG47qIEfx6FTP3sjH5NFhZNyh2UJePDB+zn9u7M3yAdMRsvvwuw3eUDeeraA1a+10xI2ZamwQnOrAP2MzEwmqBRGaX55e8kKyUpGBk0kW0PDr2Cu9bHwM82d2NQaHUqTdm8fpspXVq0XO/ZB8XHqKfGxmhKsqJS0a8A0mQeVMqQ+brOiomUKgsQFgNQeh6zt5gPuz9Ql1HlqiM+1T4I1mJ/+BIGgbObbxH4CInNtn4jwb1lVoBIsAi4Qns5nEIYF5dikSazwsIVSEV6mdTBlftaMIccjjiDRoSoj/usRItG1qzolWdHArHXWI9yVZiDVAUE7HZ5pWUI81ZgTtmvVBVLv1vcJu1kNNlmE6t/cUShgeUK4wNvqALoO5qUIaEf5a2uiwGX6/nW5Z2Yvs51J6x5nRRsHgZG5Sv1kgW+D6Tq3nX2FQUDTxPeZL7KpJywaJau1C6qR873eMnzwA9zgu3xt0eXHPhAtxP5gIdO8zYdZJwwvDnjpmz4dE6hgoZIDTJ0nbJNFh55mPc5jDtCcRvUqB5SVnsxo4DpzMG2zHK4UH2EU0DjCJqUeEbJXwjXtJJldEUGWCqH4ZTxUa89DPczgi2vbZi9IdMFgpLgK+66wD2x1CC/1afTUMEl8L0=",
        ),
        MapTraceEvent(
            start=4200,
            total=4739,
            data="XQAABADoAwAAAC3//g9vLf0BAiLh0C1Un665COfziot1ZmldOUbLEljsuAg6O6vlHZ1ckG5vfCgExDK21UGT8IlMb78qRC+eVfn4Eue+0rkXOfu+zomiDeeJnvJS51MhOfKEgra/JIE/lyalimYZ1ZfGCKOc9DSjuxEi/KwetYZaFPxkVmDenAn2egEwBBK4x2Buz7kH/9CgS/dn2ZHfROMiuJHYEyUXGcDW+t9OSA1GjzAukPN9cz/IxxhGqIWeu4PPTaKUNmXL3USlNjuBtmU4Tv7FaiwH+7leFIofxML3txH0kiOCl1PGyM4HD5lS5AQANquI4aXNSpylDRbAfPC/yteOkMjMCE/xvcC5vdVxHspvat//rfO2QoxkzK+0WRZSxeu93o/IXJuXPz1RhkQz4dseKcdwm1sKSVFtM6H9GN0lepWZMTTTp5oosPLvjYXGP7ZYX3tnr5xwOXIdgvxw/pDeF89UCRoXSH4dlUNEhGf5a3mklbAhtO1ZfSf6bPY/1ue9k9+h5RemKEFmsmaY4lsOEj2DbrfPvPbCrmRfsMu6YUp5JR9eQbvaBVJfl69mn873/HyoQRBTwo+fL+bW7Bee0xKlPRbBBxCxlkI1h7Ok8PcM2w0bSbtNys4txzPkvQUK1dyeUDTqeNdGiHnEkbm+jHsVkuTCIyj3/8LQbKbou8QMoVle/7ZyxlSx/OtWZNn7zWrBVr7nHc+uollNrCuUfyt899qgjbSHO83thNfiQs7nR9GphhQHiLsYg7E0cS45z+LIsqeWDTDOfuSgnhK49CTOLhNSXgA=",
        ),
        MapTraceEvent(
            start=4400,
            total=4739,
            data="XQAABADoAwAAAFAAWZBszgDAX7GMUAs9P2fe2hlqEA7N3dsyPePDguFw2duGJrKri1JcbAVjkJiw99K6tZTFJIqxwMdXXQbf+fujYBZAI7EmTavJI+gLoU/NF/4JS7kHtK2xgC9N+5zU+uBqzafLvY/olqkSckXS5IpKNqQPTX2PeTn+khpBpG8gQ0b9I2X1UDbTcg5xdGJJLbBPtOpjHjlEdgFcswLFE2OGs5Dt2qgEvf+51Kl3ufNniT8E/wt0oRB+HWPr1iJXd9YO3jGxBj3vA0PsZn5lmI4PDxjOlaWl5/H8swLzS8mJ4hft6EOzDYV8+fotP7Nj9BW/CIZ5yH1WFWiAkjfNv7cKHTI5yH6xtzjzwD2axNhaU65PTrxOv3OmIzJ66Ro7fD3wcDsVWtaLVgmPqLW0Yu3XhaQDwmpeJ7VcgYf5KbQeMiCVzHDL3ZswfhJmDp7CkgxgT9shdtHYHBa4/hkaBvXc4gKhr48p8WAWVRyhIk6B+uC8j5+iaK0BuvI7HBBf8B6mfK82u4g2k8hlp9aF/nqAWjqzkKn8Crigw4zVwAfVtAN0iJuWIp1ox0Sg+OI8NGAQUubetPj7l7djXHfvTQkTPwqaEKysDnWyr5qSnYsfO4IP3Xbr0rHc/69nrlqHoXCxe+iwsgjObA7sV8wAHTNf1mV//msCYuHNL6EGghdXeXqlNqf5/pERjI+Kf0kXirW9ZfaM8hnwsu3DPkbaTdJ6FF5cww==",
        ),
        MapTraceEvent(
            start=4600,
            total=4739,
            data="XQAABAC3AgAAAEAARrdhQjJgt6Qn+EaHUnhtBqcbRDJt7MLo1Z37lF/8QWg0KUCq9lx6rbNOO8aMysAimBy1sUGefkUEhZu/XcDUcvqb2P2ohSjvV6akkGdG2Jg6Q+WfObCqNwgi55dn7PeR3OIzq9Q9IvgTbGE3wcAOK51vI5rqrw0JRqkeMIt56lmDCGRWaiiw3ydmwYUT0NSMJixjd1F12AZyDnhXLqVu+oHguEtwWen2bSgDpQowWZ/79jZOKiBjPVfRNp/Jda8xZvOPd0f5s64BdTXbhTBArcQ/gMg0gcZSD5RnDSNL0jGt74LZtOy6oL/Q0b+hJd6g8gC7G8LWhgY5RucJoq2MZXhoxgdatdAJDUWhyWvxc+n7E2fpfXCCBPlEOl2PRR4f2NktXTBFdizFjeUHefZABceGJo0rRYlq4HlesvczC5kbciiIFhvtZFzHJebBWeH1Xd2RFqlxjP2qlWDvqoSrEKctwk6G0tumLf+pE+Iebzf8koLKmsvwRdBcOrEqfkEek61DFPTtyRH/GihnJfyw6xJNyC0ac8eKJWy+JYRrqGcm1i3c",
        ),
    ]
