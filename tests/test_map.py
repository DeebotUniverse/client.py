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
    Path,
    Point,
    TracePoint,
    ViewBoxFloat,
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
    from deebot_client.events.base import Event

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
    ("x", "y", "view_box", "expected"), _test_calc_point_in_viewbox_data
)
def test_calc_point_in_viewbox(
    x: int,
    y: int,
    view_box: ViewBoxSpec,
    expected: Point,
) -> None:
    result = _calc_point_in_viewbox(x, y, ViewBoxFloat(view_box))
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
    "deebot_client.map.decompress_7z_base64_data",
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
        (
            MapSubsetEvent(
                id=0,
                type=MapSetType.VIRTUAL_WALLS,
                coordinates="['12023', '1979', '12135', '-6720']",
            ),
            Path(
                stroke="#f00000",
                stroke_width=1.5,
                stroke_dasharray=[4],
                vector_effect="non-scaling-stroke",
                d=[MoveTo(x=240.46, y=-39.58), LineToRel(dx=2.24, dy=173.98)],
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
    ("positions", "view_box", "expected"), _test_get_svg_positions_data
)
def test_get_svg_positions(
    positions: list[Position],
    view_box: ViewBoxSpec,
    expected: list[Use],
) -> None:
    result = _get_svg_positions(positions, ViewBoxFloat(view_box))
    assert result == expected


async def test_get_svg_map(
    execute_mock: AsyncMock,
    event_bus: EventBus,
) -> None:
    """Test getting svg map."""
    map = Map(execute_mock, event_bus)

    async def on_change(_: MapChangedEvent) -> None:
        pass

    event_bus.subscribe(MapChangedEvent, on_change)
    await block_till_done(event_bus)

    for event in _events_for_map_test():
        event_bus.notify(event)

    await block_till_done(event_bus)

    svg_map = map.get_svg_map()
    assert (
        svg_map
        == '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-26 -53 350 180"><defs ><radialGradient id="dbg" cx="50%" cy="50%" r="50%" fx="50%" fy="50%"><stop style="stop-color:#00f" offset="70%"/><stop style="stop-color:#00f0" offset="97%"/></radialGradient><g id="d"><circle r="5" fill="url(#dbg)"/><circle stroke="white" stroke-width="0.5" r="3.5" fill="blue"/></g><g id="c"><path d="M4-6.4C4-4.2 0 0 0 0s-4-4.2-4-6.4 1.8-4 4-4 4 1.8 4 4Z" fill="#ffe605"/><circle cy="-6.4" r="2.8" fill="#fff"/></g></defs><image style="image-rendering: pixelated" href="data:image/png;base64,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" x="-26" y="-53" width="350" height="180"/><path stroke="#f00000" stroke-dasharray="4" stroke-width="1.5" vector-effect="non-scaling-stroke" d="M240.46-39.58l2.24 173.98"/><path stroke="#f00000" stroke-dasharray="4" stroke-width="1.5" vector-effect="non-scaling-stroke" d="M42.4 91.62l-0.28 33.8"/><path stroke="#fff" stroke-width="1.5" vector-effect="non-scaling-stroke" transform="scale(0.2 -0.2)" d="M0 1h-10l3-9 7-7 6-8 5-9 10 2h10l9-4 6-8 7-9-1-10-4-9-4-9-10-4h-10l-10 1-8 6-6 8-2 9 2 11 3 10 8 6 10 3v10l-7 7-9 5 7-7 9-4 10-2h10l10-4 7-7 6-8 6-8" stroke-linejoin="round" fill="none"/><use href="#d" x="-8.0" y="7.16"/><use href="#c" x="-8.0" y="7.16"/></svg>'
    )


def _events_for_map_test() -> list[Event]:
    """Events for map test."""
    return [
        PositionsEvent(
            positions=[
                Position(type=PositionType.DEEBOT, x=-400, y=-358, a=43),
                Position(type=PositionType.CHARGER, x=-400, y=-358, a=43),
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
                "652761817",
                "3897196952",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1037493650",
                "166816722",
                "3059522245",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "2736690636",
                "4255162210",
                "298631438",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "1295764014",
                "2295463665",
                "78164421",
                "2619958765",
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
            total=35,
            data="XQAABACvAAAAAAAAAEINQkt4BfqEvt9Pow7YU9KWRVBcSBosIDAOtACCicHy+vmfexxcutQUhqkAPQlBawOeXo/VSrOqF7yhdJ1JPICUs3IhIebU62Qego0vdk8oObiLh3VY/PVkqQyvR4dHxUDzMhX7HAguZVn3yC17+cQ18N4kaydN3LfSUtV/zejrBM4=",
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
        MinorMapEvent(
            index=27,
            value="XQAABAAQJwAAAABv/f//o7f/Rz5IFXI5YVG4kijmo4YH+e7kHoLTL8U6OoIUllGvXGckqgrY3KwNpyZGro/5e86CkfTA/8SmXTF6vyQbpfm3aKaB+BUT4HR4Nh+9bBIA2F6P732TMOPPUVCNgk0iTfsofTrBHnDwU1v6Vu89JmUeZ4WnTF6XnZm4TLATbNsidiEYdPjJtfGfc/aBpCFaBu4OUZWDkCbTfRxll4st1S/a9536TigRw5i94zhfAA==",
        ),
        MinorMapEvent(
            index=28,
            value="XQAABAAQJwAAAABv/f//o7f/Rz5IFXI5YVG4kijmo4YH+e7kHoLTL8U6O/tP7Y2EYYVDkNYQ8LR1ByAxWylpYxNq9+RlCIPZ1PEy+i79EP/P9zFmbs/FXBaDyknS4oOvAx6U",
        ),
        MapSubsetEvent(
            id=5,
            type=MapSetType.ROOMS,
            coordinates="-1074,-474;-574,-474;-424,-624;-424,-674;-374,-724;-374,-1224;925,-1224;975,-1274;975,-1624;1025,-1574;1025,-1524;1075,-1474;1775,-1474;1775,-774;1825,-724;1875,-724;1925,-774;1925,-1174;2525,-1174;2525,175;2175,175;2125,225;2175,275;2325,275;2325,475;2225,475;2175,525;2225,575;2475,575;2475,675;2525,725;2575,675;2575,275;3425,275;3425,775;3175,775;3125,825;3125,875;3175,925;3425,925;3425,1925;3125,1925;3075,1975;3075,2125;2925,2125;2875,2175;2875,2475;1675,2475;1675,2175;1625,2125;1575,2175;1575,2525;425,2525;425,1875;375,1825;-1074,1825",
            name="Wohnzimmer",
        ),
        MapSubsetEvent(
            id=3,
            type=MapSetType.ROOMS,
            coordinates="3175,-4825;3425,-4825;3475,-4874;3475,-6075;3925,-6075;3975,-6124;3975,-6325;4525,-6325;4525,-6224;4575,-6174;4675,-6174;4675,-5325;4475,-5325;4425,-5274;4425,-5224;4475,-5174;4775,-5174;4775,-3574;4225,-3574;4175,-3524;4175,-3024;3625,-3024;3625,-3174;3575,-3224;3425,-3224;3425,-3474;3375,-3524;3325,-3524;3275,-3474;3275,-3324;3175,-3324",
            name="Badezimmer",
        ),
        MapSubsetEvent(
            id=8,
            type=MapSetType.ROOMS,
            coordinates="-1274,-2874;-1174,-2874;-1174,-2824;-1124,-2774;1175,-2774;1225,-2824;3575,-2824;3625,-2874;3625,-2974;4175,-2974;4175,-2874;4225,-2824;6325,-2824;6375,-2874;6375,-2974;6375,-2924;6425,-2874;7175,-2874;7225,-2924;7225,-2974;7325,-2974;7275,-2974;7225,-2924;7225,-2874;7275,-2824;8375,-2824;8375,-1924;8425,-1874;8325,-1774;5675,-1774;5675,-1874;5625,-1924;4775,-1924;4725,-1874;4725,-1724;4675,-1724;4625,-1674;4625,-1374;4325,-1374;4275,-1324;4075,-1324;3975,-1224;3975,-1174;3925,-1174;3975,-1224;3925,-1274;3775,-1274;3775,-1624;3725,-1674;1825,-1674;1775,-1624;1775,-1524;1075,-1524;1075,-1574;925,-1724;-1274,-1724",
            name="Flur",
        ),
        MapSubsetEvent(
            id=4,
            type=MapSetType.ROOMS,
            coordinates="3625,-1174;3875,-1174;3925,-1124;3975,-1124;4025,-1174;4025,-1224;4075,-1274;4275,-1274;4325,-1324;4625,-1324;4625,-1274;4675,-1224;4825,-1224;4825,-874;4875,-824;5075,-824;5075,-724;5125,-674;6675,-674;6675,-624;6725,-574;6975,-574;7025,-624;7025,-1074;7525,-1074;7525,-524;7325,-524;7275,-474;7275,-124;7075,-124;7025,-74;7025,-24;7075,25;7675,25;7675,225;7725,275;7925,275;7925,1325;7775,1325;7725,1375;7725,1475;7775,1525;7875,1525;7875,1775;6575,1775;6575,1475;6525,1425;6075,1425;6025,1475;6075,1525;6375,1525;6375,1975;6425,2025;6575,2025;6575,2375;6075,2375;6025,2425;6025,2625;5325,2625;5325,2525;5275,2475;4275,2475;4275,-174;4225,-224;3925,-224;3925,-524;3875,-574;3625,-574",
            name="Büro",
        ),
        MapSubsetEvent(
            id=10,
            type=MapSetType.ROOMS,
            coordinates="-1174,-4674;-874,-4674;-824,-4724;-824,-5724;2125,-5724;2125,-5575;2175,-5524;2825,-5524;2825,-4924;2575,-4924;2525,-4874;1625,-4874;1575,-4825;1575,-2924;1225,-2924;1175,-2874;1175,-2824;-1124,-2824;-1124,-2874;-1074,-2874;-1024,-2924;-1074,-2974;-1174,-2974;-1174,-3324;-874,-3324;-824,-3374;-824,-3424;-874,-3474;-1174,-3474",
            name="Küche",
        ),
        MapSubsetEvent(
            id=9,
            type=MapSetType.ROOMS,
            coordinates="8375,-1774;8475,-1874;8425,-1924;8425,-2824;8475,-2824;8525,-2874;8525,-3124;9075,-3124;9125,-3174;9075,-3224;8525,-3224;8525,-4624;9125,-4624;9125,-4174;9175,-4124;9225,-4174;9225,-4774;9175,-4825;8525,-4825;8525,-5924;12075,-5924;12125,-5974;12125,-6075;12525,-6075;12525,-5924;12575,-5874;13875,-5874;13875,-5724;13925,-5674;14375,-5674;14425,-5724;14425,-5974;15375,-5974;15375,-5674;14975,-5674;14925,-5624;14925,-5374;14375,-5374;14325,-5325;14375,-5274;14825,-5274;14825,-4874;14075,-4874;14025,-4825;14025,-4774;13425,-4774;13375,-4724;13375,-4325;13425,-4274;13825,-4274;13825,-4024;13575,-4024;13525,-3974;13525,-3674;13575,-3624;13775,-3624;13775,-3424;13825,-3374;13925,-3374;13925,-2074;13525,-2074;13475,-2024;13475,-1824;13525,-1774;13975,-1774;14025,-1824;14025,-2624;14875,-2624;14875,-2524;14925,-2474;15275,-2474;15325,-2524;15325,-2674;16125,-2674;16125,-2524;16025,-2524;15975,-2474;15975,-1974;14475,-1974;14425,-1924;14425,-1674;14475,-1624;15325,-1624;15325,-1374;15075,-1374;15025,-1324;15075,-1274;15475,-1274;15475,-324;15175,-324;15125,-274;15125,-224;13525,-224;13475,-174;13525,-124;14725,-124;14725,-24;14775,25;15375,25;15375,325;14375,325;14325,375;14375,425;15125,425;15125,525;15175,575;15475,575;15475,1425;15225,1425;15175,1475;14725,1475;14675,1525;14675,1725;12675,1725;12675,925;12625,875;12575,875;12525,925;12525,1625;12125,1625;12125,675;12075,625;12025,625;11975,675;11975,1725;9225,1725;9225,1425;9175,1375;8875,1375;8825,1425;8825,1675;8525,1675;8525,-1724;8475,-1774",
            name="Wintergarten",
        ),
        MapSubsetEvent(
            id=7,
            type=MapSetType.ROOMS,
            coordinates="5075,-4474;5575,-4474;5625,-4524;5625,-6325;7325,-6325;7325,-4374;7375,-4325;7425,-4374;7425,-5974;8075,-5974;8075,-4274;7975,-4274;7925,-4224;7925,-3824;7575,-3824;7525,-3774;7525,-2974;7375,-2974;7325,-3024;7225,-3024;7175,-2974;7175,-2924;6425,-2924;6425,-2974;6375,-3024;6375,-3824;6325,-3874;6275,-3874;6225,-3824;6225,-3574;5075,-3574",
            name="Schlafzimmer",
        ),
        MinorMapEvent(
            index=34,
            value="XQAABAAQJwAAAABugkgp5bzuDTsxgTfHTugMraGXP+ltaKAyC/YRb7guQlLvRs3pB8oB2eN85q4BuFvjNcnL2R9zlaWiYy8lilO/Mh3qPXSR7uNinsSaPtMOdXeDHC1pkpU02xnWK/qQBNAC1B+ncz1tePV7ybL7gpMnZLISW5ZG3pqqghgSRuA=",
        ),
        MinorMapEvent(
            index=35,
            value="XQAABAAQJwAAADfuKAXQNczI4gAIXkUZbxSKxosq0+XZzOajuOyPl9wWdg3EwBu+azWjbNbUz666XGaYC3gUR+F1Cb5IWCFnqbndxSgwtgNiAPLo9M2Ipn+mB9ZIzkWLVouj8UF//TcugHTWJ1kwiS27tm/4TZxarvpI5RoVG1rRwbgVe6b6uhSt1BHuWEkL2EgrA32jzQGOwwnRrQGOx5jYZop8R7sXCo9508Rkiv0E9ezyKq5wQLnOPppspzs1vHYgLNV8UcOKchfAOfWQAW4BGUupPdrkskIUMw1A0LCgkdfwp/JCfSDPhtWqGnD5htDijz+52sT+52scY4KwYe7L3O/2lEKkGxG8UQPbyDGX1A==",
        ),
        MinorMapEvent(
            index=36,
            value="XQAABAAQJwAAADVuIATZv7b3qYZ+EcqBeKoxiESZjVeBXbaP4M86YXV4mh7ZG/frZiwmDHyYVuT6iMBXbrEvdUz13BLebxWB4Irc67tBA+hOe5hePKz4Xn83vhUceNl1crFlgzOivS9TvfHlVLe3O5QxeueJyjM/7aG23GwXqPMoeJPVzz17Zx+F1JnOIYr3hi6Qa+0pWqVTePoz1VrHNW2Pa8GFRAIPGCD4Fz+rkN2h5WccfOaZ4uKi4IiMww==",
        ),
        MinorMapEvent(
            index=42,
            value="XQAABAAQJwAAAABubEsjyjym4p3tetMqOx59dgIvptMvdoM4GxpnShdpXptVMLzFuYVDRf7/h/S7UPCRO4eeAoCtxihXhsGWRAB8T4dLkNtTamGpWIlWwDBygo7emXe1+tSSSFL7jgb728ddCkaFlPxBn4oNQBE3Q+QdC5k4gh3pgb314puwRhjXEtc952WgQ05xy6W97oYmLtk2FadXPJXyXUUVPH1Zw2OX48vTiLITEro4ClqFHXevQTRuqLDy1gHC0GS+xoMUwArUl5wm2dS7zaA=",
        ),
        MinorMapEvent(
            index=43,
            value="XQAABAAQJwAAAAJuJAACx4OBcQprP91YASA7KCbdhQbxy2wl6f6aGqcvnCpJECtL1cqKITtl8qDVmgho3vYlUYorTlB2GZ17Lq2boEnJFFVoz0YEPiclQR8l7RVNAYDAAkEJaWNT6CA+TVx9+tNvQev54U2vE9fLG5G/QC7kQqiEBxnYkvfGwCUg7GRHrE/3jUWZ/n0mCAFW9iNnYCyhDQ3cPwTsMIiqkdNwD2OQlHWlFZs2C/A37NLjnzIpKrdvm2H/oWyEf4+qqOEH85dUiQ9k5FRfx2pfKhL8A42ZgA4C623W26zXcSl7Vlgrm7sBicJbTVTRwTY5HufJkZ+aYsn6TNvUhKY/zvgA",
        ),
        MinorMapEvent(
            index=44,
            value="XQAABAAQJwAAADTuOgQB/72wZx/w8zQuXJA7zMEekl0dPMB8OvQiz3AkdtwkgOUDB5hW9x0BLag1lRbKqjYgKc0NhT/ebcTX57E4ETcwZ+8ptzWztNzk1Kh+poLJXLouDpCNENY8ZY/+2pAopPvMtWH5w9ftXNoBr51d8MLRGJw6vqw72JJqnAaEryA=",
        ),
        MinorMapEvent(
            index=50,
            value="XQAABAAQJwAAAABuekhJZt5pbU4RwYAHIDtReEcz/S9uYyPJr+DpMLWpsnw6WqOhWKh7QfXFTlx0h5RHxZrYItBKU+9ZoSx939S5IfAB2QNSiaD7oyz180jVKegOv0CoeKW5rEmG5WYQspq+xJ8AAA==",
        ),
        MinorMapEvent(
            index=51,
            value="XQAABAAQJwAAADdt/gXVg0greQ8SOVJWwRx/WGMASUHLAUJaxnPABa/xpu01j1MnlZ5Cw9kqBnzhE4LNyfUIxhAjQsTur5wf4jpbQVR9fhC9QIdo4KEwTqJOxqhVbWGDwoAXsJfCXnocOWFUfMDoAYA6WIcyUy1abkvM7S+G3+WfdJ79yn9yqGwHLF/BDsLRP5sWkC0xfEbYG3/kVTvVuer9tkJJZuUtPuoDeke7jtt7fbKmSdRlqV8W4ryky9MwxQGaG2rVUFMTA/21VA36oME8BgiPf8tluiJBqIVS3LenDFSx4TlEHRDvIvgiUTLoR9kgZS39pEXmzvwyfRTfhD89aZBYncw+/WHT9c75Qp0JM+5jbp++7Ti/qcY5rSf4qA8h9OLnsVQpP5vHDrsH5SsTqob/rd/aXyyhwKF75/aVb1SCXCtRpLuZQLLF9ysn9xUUIBItgbxTU4Y85Cny8zRYCnIMyISzyu3FR18gbsQjlyHsYdP4ox+taOavKEBalU8wtmFSpMNLZPvClAqHpBEoSfH7wXbwS/waNWxhm1bduNMjYX0QocQdCItL9uSqMLhHb7gDl0DyNw==",
        ),
        MinorMapEvent(
            index=52,
            value="XQAABAAQJwAAADduHADckpSIU6Lc7gaVYbkAJ7nzivxyykJm7S5UENTnwWPpUkCxzMqUbZUSOVQynE7gXFy0B/peslyR7qCxAZQSixx4AIJgTKtHOHGEXPt5wHceFvpRYUj1Y2r2Ap7FZnNxd6gdrFj6BemyU8hHnIfgGjCPLKK8IPiDUuFDlsn0u1KjAMvgKlB/0idGrOcp6RGHSyax/VzEd6/R03+KvUGtFxDk+rptMh+PxCmkpQNySUhF0qL/5hrYErPq+18df58ID54k9vt/KDkgUZNdmWxcP93wE6hGkEPpMdavYM55ig==",
        ),
        MinorMapEvent(
            index=58,
            value="XQAABAAQJwAAAABueEhRYy/zcKOyJula+ms1kF6/s3HLunhYjJwX3JUQ0S4YWBPnRSjIfE3XhUM/SCd3HJoe72si",
        ),
        MinorMapEvent(
            index=59,
            value="XQAABAAQJwAAAABuPElBZUtUurqaYu0MeEeAil4++JRw2vImdzqzdC/RlvGuG6OzaK3Xuy5nIu1m+tUotWkHqnR3Fx3UnAFgYtDFmfCCLNpG3jndVAbv3p7ZKCcacQA=",
        ),
        MinorMapEvent(
            index=60,
            value="XQAABAAQJwAAADcBXQeAAHimLPzHwr4JpEB5N7g5Lk+Dg/WqdIeFBDEA0yVh4AgSu169o8v2gNILCNK85c9hT2/ETMWSbq1CxPOqitsPIFQNsni7AA==",
        ),
    ]
