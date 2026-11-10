"""Integration tests for Map with native map and trace streams."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

from deebot_client.commands.json.native_map import GetNativeMapData
from deebot_client.events import (
    CachedMapInfoEvent,
    MapChangedEvent,
    NativeMapEvent,
    NativeTraceEvent,
    Position,
    PositionsEvent,
)
from deebot_client.events.map import Map as SavedMap
from deebot_client.hardware.cqyi87 import get_device_info
from deebot_client.map import Map
from deebot_client.map_data import MapData
from deebot_client.rs.map import PositionType, RotationAngle
from tests.common import block_till_done

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

SYNTHETIC_LZ4_5X3 = "8AD/AAAAAQAAAAAAAgAAAAM="
SYNTHETIC_TRACE_2PTS = "oAoAFAAADwAZAAA="
SYNTHETIC_TRACE_1PT = "UBQAHgAA"

_TRACE_PATH_RE = re.compile(
    r'<path(?=[^>]*transform="scale\(0\.2-0\.2\)")[^>]*d="([^"]+)"'
)


def trace_d(svg: str | None) -> str | None:
    """Return the cleaning-trace path data, or None when no trace renders."""
    if svg is None:
        return None
    match = _TRACE_PATH_RE.search(svg)
    return match.group(1) if match else None


def synthetic_raster(map_id: str) -> NativeMapEvent:
    """Build the synthetic 5x3 raster event used across native tests."""
    return NativeMapEvent(
        map_id=map_id,
        width=5,
        height=3,
        x_min=120,
        y_max=230,
        resolution=5,
        base64_map=SYNTHETIC_LZ4_5X3,
    )


async def test_native_map_data_svg_rendering(event_bus: EventBus) -> None:
    map_data = MapData(event_bus)
    map_data.set_native_raster(synthetic_raster("1"))
    map_data.set_native_trace(SYNTHETIC_TRACE_2PTS, 16, 0, 2)
    map_data.update_positions([Position(type=PositionType.DEEBOT, x=0, y=0, a=0)])

    svg = map_data.generate_svg()
    assert svg is not None
    assert 'viewBox="-292 -184 29 27"' in svg
    assert trace_d(svg) is not None


async def test_map_inspection_vs_active_switch(event_bus: EventBus) -> None:
    execute_mock = Mock()
    cap_map = get_device_info().capabilities.map
    assert cap_map is not None
    map_obj = Map(execute_mock, event_bus, cap_map)

    async def on_changed(_: MapChangedEvent) -> None:
        pass

    event_bus.subscribe(MapChangedEvent, on_changed)
    await block_till_done(event_bus)

    event_bus.notify(
        CachedMapInfoEvent(
            maps={
                SavedMap(
                    id="2", name="M2", using=True, built=True, angle=RotationAngle.DEG_0
                ),
                SavedMap(
                    id="3",
                    name="M3",
                    using=False,
                    built=True,
                    angle=RotationAngle.DEG_0,
                ),
            }
        )
    )
    await block_till_done(event_bus)

    event_bus.notify(
        PositionsEvent(
            positions=[Position(type=PositionType.DEEBOT, x=100, y=100, a=0)],
            map_id="2",
        )
    )
    await block_till_done(event_bus)
    assert map_obj.current_map_id == "2"
    assert len(map_obj._map_data._positions) == 1

    map_obj.select_map("3")
    await block_till_done(event_bus)
    assert map_obj.current_map_id == "3"
    assert len(map_obj._map_data._positions) == 0

    event_bus.notify(
        PositionsEvent(
            positions=[Position(type=PositionType.DEEBOT, x=200, y=200, a=0)],
            map_id="2",
        )
    )
    await block_till_done(event_bus)
    assert len(map_obj._map_data._positions) == 0

    event_bus.notify(
        PositionsEvent(
            positions=[Position(type=PositionType.DEEBOT, x=300, y=300, a=0)],
            map_id="3",
        )
    )
    await block_till_done(event_bus)
    assert len(map_obj._map_data._positions) == 1
    assert map_obj._map_data._positions[0].x == 300

    await map_obj.teardown()


async def test_trace_reset_overlap_deduplication_and_no_fabricated_head(
    event_bus: EventBus,
) -> None:
    async def on_changed(_: MapChangedEvent) -> None:
        pass

    event_bus.subscribe(MapChangedEvent, on_changed)
    await block_till_done(event_bus)

    execute_mock = Mock()
    cap_map = get_device_info().capabilities.map
    assert cap_map is not None
    map_obj = Map(execute_mock, event_bus, cap_map)
    await block_till_done(event_bus)

    map_obj.select_map("1")
    await block_till_done(event_bus)
    map_obj._map_data.set_native_raster(synthetic_raster("1"))
    await block_till_done(event_bus)

    event_bus.notify(
        NativeTraceEvent(
            map_id="1",
            trace_id=10,
            start=0,
            total_count=2,
            lz4_len=16,
            base64_trace=SYNTHETIC_TRACE_2PTS,
        )
    )
    await block_till_done(event_bus)
    svg_two = map_obj.get_svg_map()
    assert trace_d(svg_two) is not None

    event_bus.notify(
        NativeTraceEvent(
            map_id="1",
            trace_id=10,
            start=1,
            total_count=3,
            lz4_len=8,
            base64_trace=SYNTHETIC_TRACE_1PT,
        )
    )
    await block_till_done(event_bus)
    svg_overlap = map_obj.get_svg_map()
    assert trace_d(svg_overlap) is not None
    assert trace_d(svg_overlap) != trace_d(svg_two)

    event_bus.notify(
        NativeTraceEvent(
            map_id="999",
            trace_id=10,
            start=0,
            total_count=2,
            lz4_len=16,
            base64_trace=SYNTHETIC_TRACE_2PTS,
        )
    )
    await block_till_done(event_bus)
    assert map_obj.get_svg_map() == svg_overlap

    event_bus.notify(
        NativeTraceEvent(
            map_id="1",
            trace_id=11,
            start=0,
            total_count=2,
            lz4_len=16,
            base64_trace=SYNTHETIC_TRACE_2PTS,
        )
    )
    await block_till_done(event_bus)
    svg_reset = map_obj.get_svg_map()
    assert trace_d(svg_reset) == trace_d(svg_two)
    assert trace_d(svg_reset) != trace_d(svg_overlap)

    await map_obj.teardown()


async def test_new_trace_id_midstream_preserves_prior_trace(
    event_bus: EventBus,
) -> None:
    """Given valid trace, when new id starts midstream, then old kept."""
    execute_mock = Mock()
    cap_map = get_device_info().capabilities.map
    assert cap_map is not None

    async def on_changed(_: MapChangedEvent) -> None:
        pass

    event_bus.subscribe(MapChangedEvent, on_changed)
    await block_till_done(event_bus)
    map_obj = Map(execute_mock, event_bus, cap_map)
    await block_till_done(event_bus)
    map_obj.select_map("1")
    map_obj._map_data.set_native_raster(synthetic_raster("1"))
    event_bus.notify(
        NativeTraceEvent(
            map_id="1",
            trace_id=10,
            start=0,
            total_count=2,
            lz4_len=16,
            base64_trace=SYNTHETIC_TRACE_2PTS,
        )
    )
    await block_till_done(event_bus)
    valid_d = trace_d(map_obj.get_svg_map())
    assert valid_d is not None

    event_bus.notify(
        NativeTraceEvent(
            map_id="1",
            trace_id=11,
            start=1,
            total_count=3,
            lz4_len=8,
            base64_trace=SYNTHETIC_TRACE_1PT,
        )
    )
    await block_till_done(event_bus)
    assert trace_d(map_obj.get_svg_map()) == valid_d
    assert execute_mock.called

    await map_obj.teardown()


async def test_empty_start_zero_clears_prior_trace(event_bus: EventBus) -> None:
    """Given valid trace, when empty start-0 total-1, then trace cleared."""
    execute_mock = Mock()
    cap_map = get_device_info().capabilities.map
    assert cap_map is not None

    async def on_changed(_: MapChangedEvent) -> None:
        pass

    event_bus.subscribe(MapChangedEvent, on_changed)
    await block_till_done(event_bus)
    map_obj = Map(execute_mock, event_bus, cap_map)
    await block_till_done(event_bus)
    map_obj.select_map("1")
    map_obj._map_data.set_native_raster(synthetic_raster("1"))
    event_bus.notify(
        NativeTraceEvent(
            map_id="1",
            trace_id=10,
            start=0,
            total_count=2,
            lz4_len=16,
            base64_trace=SYNTHETIC_TRACE_2PTS,
        )
    )
    await block_till_done(event_bus)
    assert trace_d(map_obj.get_svg_map()) is not None

    event_bus.notify(
        NativeTraceEvent(
            map_id="1",
            trace_id=11,
            start=0,
            total_count=1,
            lz4_len=0,
            base64_trace=None,
        )
    )
    await block_till_done(event_bus)
    assert trace_d(map_obj.get_svg_map()) is None

    await map_obj.teardown()


async def test_inspected_map_keeps_own_catalog_angle(event_bus: EventBus) -> None:
    """Given inspecting A, when catalog reports active B, then A angle kept."""
    execute_mock = Mock()
    cap_map = get_device_info().capabilities.map
    assert cap_map is not None

    async def on_changed(_: MapChangedEvent) -> None:
        pass

    event_bus.subscribe(MapChangedEvent, on_changed)
    await block_till_done(event_bus)
    map_obj = Map(execute_mock, event_bus, cap_map)
    await block_till_done(event_bus)
    event_bus.notify(
        CachedMapInfoEvent(
            maps={
                SavedMap(
                    id="2",
                    name="M2",
                    using=False,
                    built=True,
                    angle=RotationAngle.DEG_0,
                ),
                SavedMap(
                    id="3",
                    name="M3",
                    using=True,
                    built=True,
                    angle=RotationAngle.DEG_90,
                ),
            }
        )
    )
    await block_till_done(event_bus)
    assert map_obj.current_map_id == "3"
    rotation = map_obj._map_data._rotation
    assert rotation is RotationAngle.DEG_90
    map_obj.select_map("2")
    rotation = map_obj._map_data._rotation
    assert rotation is RotationAngle.DEG_0
    event_bus.notify(
        CachedMapInfoEvent(
            maps={
                SavedMap(
                    id="2",
                    name="M2",
                    using=False,
                    built=True,
                    angle=RotationAngle.DEG_0,
                ),
                SavedMap(
                    id="3",
                    name="M3",
                    using=True,
                    built=True,
                    angle=RotationAngle.DEG_90,
                ),
            }
        )
    )
    await block_till_done(event_bus)
    assert map_obj.current_map_id == "2"
    rotation = map_obj._map_data._rotation
    assert rotation is RotationAngle.DEG_0

    await map_obj.teardown()


async def test_stale_raster_and_pose_do_not_contaminate_inspection(
    event_bus: EventBus,
) -> None:
    async def on_changed(_: MapChangedEvent) -> None:
        pass

    event_bus.subscribe(MapChangedEvent, on_changed)
    await block_till_done(event_bus)

    execute_mock = Mock()
    cap_map = get_device_info().capabilities.map
    assert cap_map is not None
    map_obj = Map(execute_mock, event_bus, cap_map)
    await block_till_done(event_bus)

    map_obj.select_map("2")
    await block_till_done(event_bus)
    map_obj._map_data.set_native_raster(synthetic_raster("2"))
    svg_before = map_obj.get_svg_map()
    assert svg_before is not None

    event_bus.notify(
        PositionsEvent(
            positions=[Position(type=PositionType.DEEBOT, x=100, y=100, a=0)],
            map_id="3",
        )
    )
    await block_till_done(event_bus)
    assert len(map_obj._map_data._positions) == 0

    event_bus.notify(
        PositionsEvent(
            positions=[Position(type=PositionType.DEEBOT, x=100, y=100, a=0)],
            map_id="2",
        )
    )
    await block_till_done(event_bus)
    assert len(map_obj._map_data._positions) == 1

    event_bus.notify(
        PositionsEvent(
            positions=[Position(type=PositionType.CHARGER, x=400, y=0, a=180)],
            map_id="2",
        )
    )
    await block_till_done(event_bus)
    assert len(map_obj._map_data._positions) == 2

    await map_obj.teardown()


async def test_refresh_fetches_captured_selected_map(event_bus: EventBus) -> None:
    """Given refresh on 2 then select 3, when tasks run, then 2 fetched."""
    execute_mock = AsyncMock()
    cap_map = get_device_info().capabilities.map
    assert cap_map is not None

    async def on_changed(_: MapChangedEvent) -> None:
        pass

    event_bus.subscribe(MapChangedEvent, on_changed)
    await block_till_done(event_bus)
    map_obj = Map(execute_mock, event_bus, cap_map)
    await block_till_done(event_bus)
    map_obj.select_map("2")
    map_obj.refresh()
    map_obj.select_map("3")
    await block_till_done(event_bus)
    assert execute_mock.call_count == 3
    for pending in execute_mock.call_args_list:
        command = pending[0][0]
        assert isinstance(command, GetNativeMapData)
        assert command.map_id == "2"
    await map_obj.teardown()
    assert not map_obj._tasks


async def test_select_map_resets_rust_raster(event_bus: EventBus) -> None:
    execute_mock = AsyncMock()
    cap_map = get_device_info().capabilities.map
    assert cap_map is not None

    async def on_changed(_: MapChangedEvent) -> None:
        pass

    event_bus.subscribe(MapChangedEvent, on_changed)
    await block_till_done(event_bus)
    map_obj = Map(execute_mock, event_bus, cap_map)
    await block_till_done(event_bus)
    map_obj.select_map("2")
    map_obj._map_data.set_native_raster(synthetic_raster("2"))
    first = map_obj.get_svg_map()
    assert first is not None
    assert "data:image/png;base64," in first
    map_obj.select_map("3")
    second = map_obj.get_svg_map()
    assert second is None
    await map_obj.teardown()
