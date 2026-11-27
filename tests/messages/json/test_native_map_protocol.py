"""Tests for native map push parsing (opcode 30000)."""

from __future__ import annotations

from unittest.mock import Mock, call

from deebot_client.event_bus import EventBus
from deebot_client.events import (
    CachedMapInfoEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    NativeMapEvent,
    NativeTraceEvent,
    Position,
    PositionsEvent,
    RoomsEvent,
)
from deebot_client.events.map import Map as SavedMap
from deebot_client.message import HandlingState
from deebot_client.messages.json.native_map import (
    OnNativeMapReport,
    parse_native_map_data,
)
from deebot_client.models import Room
from deebot_client.rs.map import PositionType, RotationAngle

SYNTHETIC_LZ4_5X3 = "8AD/AAAAAQAAAAAAAgAAAAM="
SYNTHETIC_TRACE_2PTS = "oAoAFAAADwAZAAA="


def test_on_native_map_report_full_telemetry() -> None:
    bus = Mock(spec_set=EventBus)
    bus.get_last_event.return_value = None

    payload = {
        "body": {
            "data": {
                "mapId": "2",
                "mapInfos": [
                    {
                        "angle": 0,
                        "chargePos": {"a": 180, "x": 40, "y": 0},
                        "index": 1,
                        "mapId": "2",
                        "name": "First Floor",
                        "saved": 1,
                        "status": 1,
                    },
                    {
                        "angle": 90,
                        "chargePos": {"a": 90, "x": 0, "y": 0},
                        "index": 2,
                        "mapId": "3",
                        "name": "Second Floor",
                        "saved": 1,
                        "status": 0,
                    },
                ],
                "mapData": {
                    "width": 5,
                    "height": 3,
                    "xMin": 120,
                    "yMax": 230,
                    "resolution": 5,
                    "map": SYNTHETIC_LZ4_5X3,
                    "chargePos": {"a": 180, "x": 40, "y": 0},
                },
                "pos": {"a": 270, "i": 0, "x": -10, "y": 15},
                "mapTraceData": {
                    "traceId": 999,
                    "start": 0,
                    "totalCount": 2,
                    "lz4Len": 16,
                    "trace": SYNTHETIC_TRACE_2PTS,
                },
                "areas": [
                    {"id": 1, "name": "Living", "centerX": 10, "centerY": 20},
                    {"id": 2, "name": "Kitchen", "centerX": 30, "centerY": 40},
                ],
                "virtualWalls": "1,1,-100,200,300,400",
                "mopWalls": "2,2,-200,100,-200,-50,50,-50,50,100",
            }
        }
    }

    result = OnNativeMapReport.handle(bus, payload)
    assert result.state == HandlingState.SUCCESS
    assert result.args == {"map_id": "2"}

    bus.notify.assert_has_calls(
        [
            call(
                CachedMapInfoEvent(
                    maps={
                        SavedMap(
                            id="2",
                            name="First Floor",
                            using=True,
                            built=True,
                            angle=RotationAngle.DEG_0,
                        ),
                        SavedMap(
                            id="3",
                            name="Second Floor",
                            using=False,
                            built=True,
                            angle=RotationAngle.DEG_90,
                        ),
                    }
                )
            ),
            call(
                NativeMapEvent(
                    map_id="2",
                    width=5,
                    height=3,
                    x_min=120,
                    y_max=230,
                    resolution=5,
                    base64_map=SYNTHETIC_LZ4_5X3,
                )
            ),
            call(
                PositionsEvent(
                    positions=[
                        Position(type=PositionType.DEEBOT, x=-100, y=150, a=270),
                        Position(type=PositionType.CHARGER, x=400, y=0, a=180),
                    ],
                    map_id="2",
                )
            ),
            call(
                NativeTraceEvent(
                    map_id="2",
                    trace_id=999,
                    start=0,
                    total_count=2,
                    lz4_len=16,
                    base64_trace=SYNTHETIC_TRACE_2PTS,
                )
            ),
            call(
                RoomsEvent(
                    map_id="2",
                    rooms=[
                        Room(name="Living", id=1, coordinates="100,200"),
                        Room(name="Kitchen", id=2, coordinates="300,400"),
                    ],
                )
            ),
            call(
                MapSubsetEvent(
                    id=1,
                    type=MapSetType.VIRTUAL_WALLS,
                    coordinates="-1000,2000,3000,4000",
                    map_id="2",
                )
            ),
            call(
                MapSetEvent(
                    type=MapSetType.VIRTUAL_WALLS,
                    subsets=[1],
                    map_id="2",
                )
            ),
            call(
                MapSubsetEvent(
                    id=2,
                    type=MapSetType.NO_MOP_ZONES,
                    coordinates="-2000,1000,-2000,-500,500,-500,500,1000",
                    map_id="2",
                )
            ),
            call(
                MapSetEvent(
                    type=MapSetType.NO_MOP_ZONES,
                    subsets=[2],
                    map_id="2",
                )
            ),
        ],
        any_order=True,
    )


def _notified_map_ids(bus: Mock) -> list[str]:
    ids: list[str] = []
    for pending in bus.notify.call_args_list:
        evt = pending[0][0]
        if (
            isinstance(
                evt,
                (
                    NativeMapEvent,
                    NativeTraceEvent,
                    PositionsEvent,
                    RoomsEvent,
                    MapSetEvent,
                    MapSubsetEvent,
                ),
            )
            and evt.map_id is not None
        ):
            ids.append(evt.map_id)
    return ids


def test_nested_raster_uses_fallback_and_transient_safe() -> None:
    bus = Mock(spec_set=EventBus)
    bus.get_last_event.return_value = None
    parse_native_map_data(
        bus,
        {"mapData": {"map": "eA==", "width": 1, "height": 1, "xMin": 0, "yMax": 1}},
        fallback_map_id="9",
    )
    ids = _notified_map_ids(bus)
    assert ids
    assert all(mid == "9" for mid in ids)


def test_int_map_ids_parse() -> None:
    bus = Mock(spec_set=EventBus)
    bus.get_last_event.return_value = None
    result = parse_native_map_data(
        bus,
        {
            "mapId": "5",
            "mapTraceData": {
                "lz4Len": 8,
                "mapId": 5,
                "start": 0,
                "totalCount": 2,
                "trace": "AA==",
                "traceId": 77,
            },
            "pos": {"a": 10, "i": 0, "x": 3, "y": 4},
        },
    )
    assert result.state == HandlingState.SUCCESS
    kinds = {type(pending[0][0]).__name__ for pending in bus.notify.call_args_list}
    assert "NativeTraceEvent" in kinds
    assert "PositionsEvent" in kinds


def test_nested_map_id_associates_pose_and_rooms_when_outer_missing() -> None:
    bus = Mock(spec_set=EventBus)
    bus.get_last_event.return_value = None
    parse_native_map_data(
        bus,
        {
            "mapData": {
                "mapId": "4",
                "chargePos": {"a": 0, "x": 1, "y": 2},
            },
            "pos": {"a": 0, "i": 0, "x": 3, "y": 4},
            "areas": [{"id": 1, "name": "R", "centerX": 0, "centerY": 0}],
        },
    )
    by_kind = {
        type(pending[0][0]).__name__: pending[0][0]
        for pending in bus.notify.call_args_list
    }
    assert by_kind["PositionsEvent"].map_id == "4"
    assert len(by_kind["PositionsEvent"].positions) == 2
    assert by_kind["RoomsEvent"].map_id == "4"


def test_conflicting_nested_id_does_not_contaminate_pose() -> None:
    bus = Mock(spec_set=EventBus)
    bus.get_last_event.return_value = None
    parse_native_map_data(
        bus,
        {
            "mapId": "2",
            "mapData": {
                "mapId": "4",
                "chargePos": {"a": 0, "x": 1, "y": 2},
            },
            "pos": {"a": 0, "i": 0, "x": 3, "y": 4},
        },
    )
    pose = next(
        pending[0][0]
        for pending in bus.notify.call_args_list
        if isinstance(pending[0][0], PositionsEvent)
    )
    assert pose.map_id == "2"
    assert [p.type for p in pose.positions] == [PositionType.DEEBOT]


def test_empty_catalog_clears_and_malformed_safe() -> None:
    bus = Mock(spec_set=EventBus)
    bus.get_last_event.return_value = None
    result = parse_native_map_data(bus, {"mapInfos": []})
    assert result.state == HandlingState.SUCCESS
    notified: list[object] = [c[0][0] for c in bus.notify.call_args_list]
    assert any(isinstance(e, CachedMapInfoEvent) and not e.maps for e in notified)

    bus2 = Mock(spec_set=EventBus)
    bus2.get_last_event.return_value = None
    result2 = parse_native_map_data(
        bus2, {"mapInfos": "bad", "mapData": "bad", "areas": "bad", "pos": []}
    )
    assert result2.state == HandlingState.SUCCESS
