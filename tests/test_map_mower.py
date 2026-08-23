from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, call

import orjson
import pytest

from deebot_client.capabilities import (
    CapabilityEvent,
    CapabilityMap,
    CapabilityMowerMap,
)
from deebot_client.commands.json import GetCachedMapInfo
from deebot_client.commands.xml import GetMapSt
from deebot_client.event_bus import EventBus
from deebot_client.events import (
    CachedMapInfoEvent,
    MajorMapEvent,
    MapChangedEvent,
    MapInfoEvent,
    MapSetEvent,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
    MowerMapTraceGroup,
    MowerMapTraceSegment,
    MowerStaticMapEvent,
    MowerWorkArea,
    MowerWorkAreasEvent,
    PositionsEvent,
    RoomsEvent,
)
from deebot_client.map import Map, MapData
from deebot_client.message import HandlingState
from deebot_client.messages.json.map import OnMapSetV2
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
from tests.commands.xml import get_request_xml
from tests.helpers import get_request_json, get_success_body

from .common import block_till_done

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

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


def _mower_map_capability() -> CapabilityMap:
    return CapabilityMap(
        changed=CapabilityEvent(MapChangedEvent, []),
        mower=CapabilityMowerMap(
            static=CapabilityEvent(MowerStaticMapEvent, []),
            work_areas=CapabilityEvent(MowerWorkAreasEvent, []),
        ),
    )


def _mower_event_bus(
    execute_mock: AsyncMock, static_device_info: StaticDeviceInfo
) -> tuple[EventBus, CapabilityMap]:
    capability_map = _mower_map_capability()
    capabilities = replace(static_device_info.capabilities, map=capability_map)
    return EventBus(execute_mock, capabilities), capability_map


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


async def _setup_mower_map(
    execute_mock: AsyncMock,
    static_device_info: StaticDeviceInfo,
) -> tuple[Map, EventBus]:
    event_bus, capabilities_map = _mower_event_bus(execute_mock, static_device_info)
    map_obj = Map(execute_mock, event_bus, capabilities_map)
    event_bus.subscribe(MapChangedEvent, AsyncMock())
    await block_till_done(event_bus)
    return map_obj, event_bus


async def test_map_event_adapter_changed_event_and_svg_cache(
    execute_mock: AsyncMock,
    static_device_info: StaticDeviceInfo,
) -> None:
    map_obj, event_bus = await _setup_mower_map(execute_mock, static_device_info)
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


async def test_minimal_mower_capabilities_subscribe_refresh_and_render(
    execute_mock: AsyncMock,
    static_device_info: StaticDeviceInfo,
) -> None:
    event_bus, capability_map = _mower_event_bus(execute_mock, static_device_info)
    event_bus_mock = Mock(spec_set=EventBus, wraps=event_bus)

    assert capability_map.changed.event is MapChangedEvent
    assert capability_map.cached_info is None
    assert capability_map.major is None
    assert capability_map.minor is None
    assert capability_map.position is None
    assert capability_map.rooms is None
    assert capability_map.set is None
    assert capability_map.trace is None
    assert capability_map.mower is not None
    assert event_bus.capabilities.get_refresh_commands(MowerStaticMapEvent) == []
    assert event_bus.capabilities.get_refresh_commands(MowerWorkAreasEvent) == []
    for unsupported_event in (
        CachedMapInfoEvent,
        MajorMapEvent,
        MinorMapEvent,
        PositionsEvent,
        MapTraceEvent,
        RoomsEvent,
    ):
        assert unsupported_event not in event_bus.capabilities._events

    map_obj = Map(execute_mock, event_bus_mock, capability_map)
    initial_subscription_events = [
        args.args[0] for args in event_bus_mock.subscribe.call_args_list
    ]
    assert initial_subscription_events == [
        MowerStaticMapEvent,
        MowerWorkAreasEvent,
    ]
    assert not event_bus.has_subscribers(MapSetEvent)
    assert not event_bus.has_subscribers(MapSubsetEvent)
    assert not event_bus.has_subscribers(MapInfoEvent)
    assert not event_bus.has_subscribers(RoomsEvent)

    changed = AsyncMock()
    event_bus_mock.subscribe(MapChangedEvent, changed)
    await block_till_done(event_bus)

    for unsupported_event in (
        CachedMapInfoEvent,
        MajorMapEvent,
        MinorMapEvent,
        PositionsEvent,
        MapTraceEvent,
        RoomsEvent,
    ):
        assert not event_bus.has_subscribers(unsupported_event)

    event_bus_mock.request_refresh.reset_mock()
    map_obj.refresh()
    assert event_bus_mock.request_refresh.call_args_list == [
        call(MowerStaticMapEvent),
        call(MowerWorkAreasEvent),
    ]
    await block_till_done(event_bus)
    execute_mock.assert_not_awaited()

    event_bus.notify(_small_static_map())
    event_bus.notify(_small_work_areas())
    await block_till_done(event_bus)
    svg = map_obj.get_svg_map()
    assert svg is not None
    assert "r0" in svg

    await map_obj.teardown()
    await event_bus.teardown()


async def test_optional_map_set_call_sites_skip_unsupported_commands(
    execute_mock: AsyncMock,
    static_device_info: StaticDeviceInfo,
) -> None:
    event_bus, _ = _mower_event_bus(execute_mock, static_device_info)

    map_set_result = OnMapSetV2._handle_body_data_dict(
        event_bus, {"mid": "1", "type": "ar"}
    )
    assert map_set_result.state is HandlingState.SUCCESS
    assert map_set_result.requested_commands == []

    cached_response, _ = get_request_json(
        get_success_body(
            {
                "enable": 1,
                "info": [
                    {
                        "mid": "1",
                        "index": 0,
                        "status": 1,
                        "using": 1,
                        "built": 1,
                        "name": "",
                    }
                ],
            }
        )
    )
    cached_result = GetCachedMapInfo()._handle_response(event_bus, cached_response)
    assert cached_result.state is HandlingState.SUCCESS
    assert cached_result.requested_commands == []

    xml_result = GetMapSt()._handle_response(
        event_bus, get_request_xml("<ctl ret='ok' st='built' method='auto'/>")
    )
    assert xml_result.state is HandlingState.SUCCESS
    assert xml_result.requested_commands == []

    await event_bus.teardown()


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
