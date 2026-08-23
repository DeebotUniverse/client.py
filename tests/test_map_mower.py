from __future__ import annotations

import asyncio
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import orjson
import pytest

from deebot_client.events import (
    MapChangedEvent,
    MowerMapTraceGroup,
    MowerMapTraceSegment,
    MowerStaticMapEvent,
    MowerWorkArea,
    MowerWorkAreasEvent,
)
from deebot_client.map import Map, MapData
from deebot_client.messages.json.map.o1200 import (
    decode_trimmed_lzma_bytes,
    strict_base64_decode,
)
from deebot_client.messages.json.map.on_mi import _parse_static_map
from deebot_client.messages.json.map.work_areas import (
    _MowerWorkAreaCoordinator,
    _parse_area_set_snapshot,
    _parse_on_ari_snapshot,
)
from deebot_client.rs.map import MapData as MapDataRs

from .common import block_till_done

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

    from deebot_client.event_bus import EventBus
    from deebot_client.models import StaticDeviceInfo

_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "goat_map"
_WORK_AREA_FIXTURE = orjson.loads(
    (_FIXTURE_ROOT / "work_area_snapshots.json").read_bytes()
)
_ON_MI_FIXTURE = next(
    fixture
    for fixture in orjson.loads(
        (_FIXTURE_ROOT / "onmi_info_representations.json").read_bytes()
    )
    if fixture["label"] == "request-876"
)


def _golden_static_map() -> MowerStaticMapEvent:
    event = _parse_static_map(
        {
            "mid": "1",
            "index": "0",
            "info": _ON_MI_FIXTURE["original"],
            "infoSize": _ON_MI_FIXTURE["info_size"],
        }
    )
    assert event is not None
    return event


def _golden_work_areas(static_map: MowerStaticMapEvent) -> MowerWorkAreasEvent:
    on_ari = _WORK_AREA_FIXTURE["on_ari"]
    compressed = b"".join(strict_base64_decode(chunk) for chunk in on_ari["chunks"])
    geometry = _parse_on_ari_snapshot(
        decode_trimmed_lzma_bytes(compressed, info_size=on_ari["info_size"]),
        expected_mid=on_ari["mid"],
    )
    area_set = _WORK_AREA_FIXTURE["area_set_ar"]
    metadata = _parse_area_set_snapshot(
        {
            "mid": area_set["mid"],
            "type": area_set["type"],
            "infoSize": area_set["info_size"],
            "subsets": area_set["subsets"],
        }
    )
    coordinator = _MowerWorkAreaCoordinator()
    assert coordinator.update_static_map(static_map) is None
    assert coordinator.update_geometry(geometry) is None
    event = coordinator.update_metadata(metadata)
    assert event is not None
    return event


def _small_static_map(*, mid: str = "1", step_size: int = 50) -> MowerStaticMapEvent:
    return MowerStaticMapEvent(
        mid=mid,
        groups=[
            MowerMapTraceGroup(
                group_id="boundary",
                segments=[
                    MowerMapTraceSegment(
                        points=[(0, 0), (100, 0), (100, 100), (0, 100)],
                        raw="boundary-raw",
                    )
                ],
            )
        ],
        step_size=step_size,
    )


def _small_work_areas(
    *, mid: str = "1", step_size: int = 50, x_offset: int = 0
) -> MowerWorkAreasEvent:
    return MowerWorkAreasEvent(
        mid=mid,
        areas=[
            MowerWorkArea(
                name="Area",
                geometry=MowerMapTraceGroup(
                    group_id="area-1",
                    segments=[
                        MowerMapTraceSegment(
                            points=[
                                (x_offset, 0),
                                (x_offset + 50, 0),
                                (x_offset + 50, 50),
                            ],
                            raw="area-raw",
                        )
                    ],
                ),
            )
        ],
        step_size=step_size,
    )


async def test_o1200_boundary_only_golden(
    event_bus: EventBus, snapshot: SnapshotAssertion
) -> None:
    map_data = MapData(event_bus)
    static_map = _golden_static_map()

    map_data.set_mower_static_map(static_map)

    svg = map_data.generate_svg()
    assert svg == snapshot
    assert svg is not None
    assert 'viewBox="-687 -427 802 914"' in svg


async def test_o1200_boundary_and_three_areas_golden(
    event_bus: EventBus, snapshot: SnapshotAssertion
) -> None:
    map_data = MapData(event_bus)
    static_map = _golden_static_map()
    work_areas = _golden_work_areas(static_map)

    map_data.set_mower_static_map(static_map)
    map_data.set_mower_work_areas(work_areas)

    svg = map_data.generate_svg()
    assert svg == snapshot
    assert svg is not None
    assert 'viewBox="-687 -427 802 914"' in svg
    # Five map paths plus the existing charger icon path in SVG definitions.
    assert svg.count("<path ") == 6


async def test_rendering_closes_visually_without_mutating_events(
    event_bus: EventBus,
) -> None:
    map_data = MapData(event_bus)
    static_map = _small_static_map()
    work_areas = _small_work_areas()
    original_static = deepcopy(static_map)
    original_areas = deepcopy(work_areas)

    map_data.set_mower_static_map(static_map)
    map_data.set_mower_work_areas(work_areas)
    svg = map_data.generate_svg()

    assert svg is not None
    assert svg.count('z"/>') == 3
    assert static_map == original_static
    assert work_areas == original_areas
    assert static_map.groups[0].segments[0].raw == "boundary-raw"
    assert work_areas.areas[0].geometry.segments[0].raw == "area-raw"


async def test_mismatched_mid_and_step_do_not_replace_render(
    event_bus: EventBus,
) -> None:
    map_data = MapData(event_bus)
    static_map = _small_static_map()
    matching = _small_work_areas()
    map_data.set_mower_static_map(static_map)
    map_data.set_mower_work_areas(matching)
    expected = map_data.generate_svg()
    map_data.reset_changed()

    map_data.set_mower_work_areas(_small_work_areas(mid="2", x_offset=50))
    map_data.set_mower_work_areas(_small_work_areas(step_size=25, x_offset=50))

    assert map_data.changed is False
    assert map_data.generate_svg() == expected


async def test_snapshot_replacement_and_new_mid_drop_stale_areas(
    event_bus: EventBus,
) -> None:
    map_data = MapData(event_bus)
    map_data.set_mower_static_map(_small_static_map())
    map_data.set_mower_work_areas(_small_work_areas())
    first = map_data.generate_svg()
    assert first is not None
    assert "r0" in first

    map_data.set_mower_work_areas(_small_work_areas(x_offset=50))
    replacement = map_data.generate_svg()
    assert replacement != first

    map_data.set_mower_static_map(_small_static_map(mid="2"))
    new_mid = map_data.generate_svg()
    assert new_mid is not None
    assert "r0" not in new_mid
    # Two boundary paths plus the existing charger icon path in definitions.
    assert new_mid.count("<path ") == 3


async def _setup_map(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
) -> Map:
    capabilities_map = static_device_info.capabilities.map
    assert capabilities_map is not None
    map_obj = Map(execute_mock, event_bus, capabilities_map)
    event_bus.subscribe(MapChangedEvent, AsyncMock())
    await block_till_done(event_bus)
    return map_obj


async def test_map_event_adapter_changed_event_and_svg_cache(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
) -> None:
    map_obj = await _setup_map(execute_mock, event_bus, static_device_info)
    changed = AsyncMock()
    event_bus.subscribe(MapChangedEvent, changed)
    static_map = _small_static_map()

    event_bus.notify(static_map)
    await block_till_done(event_bus)
    changed.assert_called_once()
    first = map_obj.get_svg_map()
    assert first is not None
    assert map_obj.get_svg_map() is first

    await asyncio.sleep(1.1)
    changed.reset_mock()
    event_bus.notify(_small_work_areas())
    await block_till_done(event_bus)
    changed.assert_called_once()
    with_areas = map_obj.get_svg_map()
    assert with_areas is not None
    assert with_areas != first
    assert "r0" in with_areas
    assert map_obj.get_svg_map() is with_areas

    changed.reset_mock()
    event_bus.notify(static_map)
    await block_till_done(event_bus)
    changed.assert_not_called()
    assert map_obj.get_svg_map() is with_areas


def test_rust_adapter_rejects_mixed_snapshot() -> None:
    data = MapDataRs()
    static_map = _small_static_map()

    for work_areas in (
        _small_work_areas(mid="2"),
        _small_work_areas(step_size=25),
    ):
        with pytest.raises(ValueError, match="must match"):
            data.set_mower_map(static_map, work_areas)


def test_rust_adapter_rejects_nonpositive_step() -> None:
    data = MapDataRs()
    for step_size in (0, -1):
        with pytest.raises(ValueError, match="must be positive"):
            data.set_mower_map(_small_static_map(step_size=step_size), None)
