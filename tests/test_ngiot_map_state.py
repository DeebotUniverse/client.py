from __future__ import annotations

from deebot_client.ngiot_map_parser import NgiotArea, NgiotBaseMap, NgiotMapInfo, NgiotOverlay, NgiotPoint, NgiotPose, NgiotTrace
from deebot_client.ngiot_map_state import NgiotMapStateStore


def test_map_state_store_normalizes_snapshot() -> None:
    store = NgiotMapStateStore()
    store.update_map_info(
        NgiotMapInfo(
            map_id="4",
            name="Home",
            using=True,
            angle=0,
            charge_pos=NgiotPoint(x=-100, y=300),
        )
    )
    store.update_base_map(
        NgiotBaseMap(
            map_id="4",
            width=10,
            height=20,
            total_width=800,
            total_height=800,
            resolution=5,
            x_min=100,
            y_max=200,
            direction=1,
            encoded="encoded-map",
        )
    )
    store.update_pose("4", NgiotPose(x=-95, y=295, a=90))
    store.update_trace("4", NgiotTrace(trace_id="t-1", encoded="trace", lz4_len=32, total_count=2, start=1))
    store.update_areas("4", [NgiotArea(area_id="1", name="Kitchen", polygon=[NgiotPoint(x=-100, y=300)])])
    store.update_overlays("4", [NgiotOverlay(overlay_type="virtual_walls", overlay_id="7", polygon=[NgiotPoint(x=-90, y=290)])])

    snapshot = store.get_normalized("4")

    assert snapshot is not None
    assert snapshot.is_renderable() is True
    assert snapshot.charge_pos == NgiotPoint(x=0, y=-24)
    assert snapshot.pose == NgiotPose(x=1, y=-23, a=90)
    assert snapshot.areas[0].polygon == [NgiotPoint(x=0, y=-24)]
    assert snapshot.overlays[0].polygon == [NgiotPoint(x=2, y=-22)]
    assert snapshot.trace is not None
    assert store.active_map_id == "4"


def test_map_state_store_detects_overlay_only_snapshot() -> None:
    store = NgiotMapStateStore()
    store.update_map_info(NgiotMapInfo(map_id="4", name="Home", using=True, angle=0))
    store.update_trace("4", NgiotTrace(trace_id=None, encoded="trace", lz4_len=None, total_count=0, start=0))

    snapshot = store.get("4")

    assert snapshot.has_background() is False
    assert snapshot.has_overlay_content() is True
    assert snapshot.is_overlay_only() is True
    assert store.get_active_renderable() is None
