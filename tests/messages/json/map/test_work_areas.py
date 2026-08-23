from __future__ import annotations

import base64
import hashlib
import lzma
from pathlib import Path
from typing import TYPE_CHECKING, Any

import orjson
import pytest

from deebot_client.events import (
    MowerMapTraceGroup,
    MowerMapTraceSegment,
    MowerStaticMapEvent,
    MowerWorkAreasEvent,
)
from deebot_client.message import HandlingState
from deebot_client.messages.json.map import GetAreaSet, OnArI, OnMI
from deebot_client.messages.json.map.o1200 import (
    decode_trimmed_lzma_bytes,
    parse_rle_path,
    strict_base64_decode,
)
from deebot_client.messages.json.map.on_mi import _parse_static_map
from deebot_client.messages.json.map.work_areas import (
    _AreaGeometry,
    _AreaMetadata,
    _AreaSetSnapshot,
    _extract_main_path,
    _find_registration,
    _MowerWorkAreaCoordinator,
    _OnArISnapshot,
    _parse_area_set_snapshot,
    _parse_on_ari_snapshot,
    _reset_work_area_state,
)

if TYPE_CHECKING:
    from unittest.mock import Mock

_FIXTURE_ROOT = Path(__file__).parents[3] / "fixtures" / "goat_map"
_WORK_AREA_FIXTURE = orjson.loads(
    (_FIXTURE_ROOT / "work_area_snapshots.json").read_bytes()
)
_ON_MI_FIXTURES = {
    item["label"]: item
    for item in orjson.loads(
        (_FIXTURE_ROOT / "onmi_info_representations.json").read_bytes()
    )
}
_ON_MI = _ON_MI_FIXTURES["request-876"]
_ON_ARI = _WORK_AREA_FIXTURE["on_ari"]
_AREA_SET = _WORK_AREA_FIXTURE["area_set_ar"]
_VW = _WORK_AREA_FIXTURE["area_set_vw"]


@pytest.fixture(autouse=True)
def reset_work_area_state() -> None:
    _reset_work_area_state()


def _on_mi_message(*, mid: str = "1") -> dict[str, Any]:
    return {
        "body": {
            "data": {
                "mid": mid,
                "batid": "fixture-main",
                "serial": "1",
                "index": "0",
                "using": 1,
                "type": "0",
                "info": _ON_MI["original"],
                "infoSize": _ON_MI["info_size"],
            }
        }
    }


def _on_ari_message(
    info: str,
    *,
    index: object,
    serial: object | None = None,
    info_size: int | str | None = None,
    mid: str = "1",
    batid: str = "fixture-area",
    type_value: int | str = "0",
) -> dict[str, Any]:
    return {
        "body": {
            "data": {
                "mid": mid,
                "batid": batid,
                "serial": _ON_ARI["serial"] if serial is None else serial,
                "index": index,
                "using": 1,
                "type": type_value,
                "info": info,
                "infoSize": (_ON_ARI["info_size"] if info_size is None else info_size),
            }
        }
    }


def _area_set_message(
    *,
    subsets: str | None = None,
    info_size: int | str | None = None,
    mid: str = "1",
    type_value: str = "ar",
    code: int = 0,
) -> dict[str, Any]:
    fixture = _AREA_SET if type_value == "ar" else _VW
    return {
        "body": {
            "code": code,
            "data": {
                "mid": mid,
                "aid": "not-a-work-area-id",
                "type": type_value,
                "subsets": fixture["subsets"] if subsets is None else subsets,
                "infoSize": (fixture["info_size"] if info_size is None else info_size),
            },
        }
    }


def _trimmed_lzma_base64(value: object) -> tuple[str, int]:
    decoded = orjson.dumps(value)
    full = bytearray(
        lzma.compress(
            decoded,
            format=lzma.FORMAT_ALONE,
            filters=[
                {
                    "id": lzma.FILTER_LZMA1,
                    "dict_size": 1 << 18,
                    "lc": 3,
                    "lp": 0,
                    "pb": 2,
                }
            ],
        )
    )
    full[5:13] = len(decoded).to_bytes(8, "little")
    trimmed = bytes(full[:9] + full[13:])
    return base64.b64encode(trimmed).decode("ascii"), len(decoded)


def _synthetic_static_map(
    *, mid: str = "1", start: str = "0,0", directions: str = "12345678"
) -> MowerStaticMapEvent:
    raw = f"s1;{mid};{start};{directions}"
    path = parse_rle_path(start, directions)
    return MowerStaticMapEvent(
        mid=mid,
        groups=[
            MowerMapTraceGroup(
                group_id="1",
                segments=[MowerMapTraceSegment(points=path.points, raw=raw)],
            )
        ],
        step_size=50,
    )


def _synthetic_geometry(
    area_id: str, *, mid: str = "1", start: str = "100,100", directions: str
) -> _OnArISnapshot:
    return _OnArISnapshot(
        mid=mid,
        areas=(
            _AreaGeometry(
                area_id=area_id,
                path=parse_rle_path(start, directions),
                raw=f"{area_id};{start};{directions}",
            ),
        ),
    )


def _synthetic_metadata(
    area_id: str, *, mid: str = "1", name: str = "Area"
) -> _AreaSetSnapshot:
    return _AreaSetSnapshot(
        mid=mid,
        areas=(_AreaMetadata(area_id=area_id, name=name),),
    )


def _golden_static_map() -> MowerStaticMapEvent:
    event = _parse_static_map(_on_mi_message()["body"]["data"])
    assert event is not None
    return event


def _golden_on_ari_snapshot() -> _OnArISnapshot:
    compressed = b"".join(strict_base64_decode(chunk) for chunk in _ON_ARI["chunks"])
    decoded = decode_trimmed_lzma_bytes(compressed, info_size=_ON_ARI["info_size"])
    return _parse_on_ari_snapshot(decoded, expected_mid=_ON_ARI["mid"])


def test_o1200_work_area_golden_snapshot_emits_registered_event(
    event_bus_mock: Mock,
) -> None:
    assert OnMI.handle(event_bus_mock, _on_mi_message()).state == HandlingState.SUCCESS
    for index, chunk in enumerate(_ON_ARI["chunks"]):
        assert (
            OnArI.handle(event_bus_mock, _on_ari_message(chunk, index=index)).state
            == HandlingState.SUCCESS
        )

    assert not any(
        isinstance(call.args[0], MowerWorkAreasEvent)
        for call in event_bus_mock.notify.call_args_list
    )
    assert (
        GetAreaSet.handle(event_bus_mock, _area_set_message()).state
        == HandlingState.SUCCESS
    )

    event = next(
        call.args[0]
        for call in event_bus_mock.notify.call_args_list
        if isinstance(call.args[0], MowerWorkAreasEvent)
    )
    assert event.mid == "1"
    assert event.step_size == 50
    assert [area.geometry.group_id for area in event.areas] == ["4", "1", "2"]
    assert [area.name for area in event.areas] == ["Zone 4", "Zone 1", "Zone 2"]
    assert [len(area.geometry.segments[0].points) for area in event.areas] == [
        805,
        769,
        884,
    ]
    assert all(area.geometry.segments[0].raw for area in event.areas)
    assert not hasattr(event, "batid")
    assert not hasattr(event, "transport")


def test_o1200_registration_matches_independent_reference_viewer() -> None:
    main = _extract_main_path(_golden_static_map())
    assert main is not None
    snapshot = _golden_on_ari_snapshot()
    expected = {item["area_id"]: item for item in _WORK_AREA_FIXTURE["registrations"]}

    for area in snapshot.areas:
        registration = _find_registration(main, area.path)
        assert registration is not None
        reference = expected[area.area_id]
        assert registration.main_index == reference["main_index"]
        assert registration.area_index == reference["area_index"]
        assert (
            registration.matched_direction_count == reference["matched_direction_count"]
        )
        assert len(area.path.directions) == reference["area_direction_count"]
        assert [registration.offset_x, registration.offset_y] == reference["offset"]


@pytest.mark.parametrize(("serial", "index"), [(3, 0), ("3", "0")])
def test_onArI_accepts_integer_and_canonical_decimal_indexes(
    event_bus_mock: Mock, serial: int | str, index: int | str
) -> None:
    result = OnArI.handle(
        event_bus_mock,
        _on_ari_message(_ON_ARI["chunks"][0], serial=serial, index=index),
    )

    assert result.state == HandlingState.SUCCESS
    assert len(OnArI._CHUNK_BUFFER) == 1


@pytest.mark.parametrize(("serial", "index"), [("03", "0"), ("3", "00"), (True, 0)])
def test_onArI_rejects_noncanonical_indexes(
    event_bus_mock: Mock, serial: object, index: object
) -> None:
    result = OnArI.handle(
        event_bus_mock,
        _on_ari_message(
            _ON_ARI["chunks"][0],
            serial=serial,
            index=index,
        ),
    )

    assert result.state == HandlingState.ANALYSE_LOGGED
    assert OnArI._CHUNK_BUFFER == {}


def test_onArI_missing_index_remains_incomplete(event_bus_mock: Mock) -> None:
    encoded, size = _trimmed_lzma_base64([["1", "1", "opaque", "1;0,0;12"]])
    compressed = strict_base64_decode(encoded)
    split = len(compressed) // 2

    result = OnArI.handle(
        event_bus_mock,
        _on_ari_message(
            base64.b64encode(compressed[:split]).decode(),
            serial=2,
            index=0,
            info_size=size,
        ),
    )

    assert result.state == HandlingState.SUCCESS
    assert len(OnArI._CHUNK_BUFFER) == 1
    event_bus_mock.notify.assert_not_called()


def test_onArI_duplicate_index_fails_and_drops_buffer(event_bus_mock: Mock) -> None:
    message = _on_ari_message(_ON_ARI["chunks"][0], index=0)

    assert OnArI.handle(event_bus_mock, message).state == HandlingState.SUCCESS
    assert OnArI.handle(event_bus_mock, message).state == HandlingState.ANALYSE_LOGGED
    assert OnArI._CHUNK_BUFFER == {}


def test_onArI_mixed_identity_fails_and_drops_buffer(event_bus_mock: Mock) -> None:
    assert (
        OnArI.handle(
            event_bus_mock,
            _on_ari_message(_ON_ARI["chunks"][0], serial=2, index=0),
        ).state
        == HandlingState.SUCCESS
    )

    result = OnArI.handle(
        event_bus_mock,
        _on_ari_message(_ON_ARI["chunks"][1], serial=3, index=1),
    )

    assert result.state == HandlingState.ANALYSE_LOGGED
    assert OnArI._CHUNK_BUFFER == {}


def test_onArI_in_flight_snapshot_buffer_is_bounded(event_bus_mock: Mock) -> None:
    for number in range(17):
        result = OnArI.handle(
            event_bus_mock,
            _on_ari_message(
                _ON_ARI["chunks"][0],
                index=0,
                batid=f"fixture-area-{number}",
            ),
        )
        assert result.state == HandlingState.SUCCESS

    assert len(OnArI._CHUNK_BUFFER) == 16
    assert all(identity.batid != "fixture-area-0" for identity in OnArI._CHUNK_BUFFER)


@pytest.mark.parametrize(
    ("info", "info_size"),
    [
        ("not-base64", 1),
        ("AAAA", 1),
        _trimmed_lzma_base64("not-json-object"),
        _trimmed_lzma_base64([["1", "2", "opaque", "ignored"]]),
        _trimmed_lzma_base64([["1", "1", "opaque", "broken-record"]]),
    ],
    ids=["base64", "lzma", "json", "unknown-layer", "unknown-record"],
)
def test_onArI_malformed_or_unknown_complete_snapshot_fails_closed(
    event_bus_mock: Mock, info: str, info_size: int
) -> None:
    result = OnArI.handle(
        event_bus_mock,
        _on_ari_message(info, serial=1, index=0, info_size=info_size),
    )

    assert result.state == HandlingState.ANALYSE_LOGGED
    event_bus_mock.notify.assert_not_called()


def test_getAreaSet_empty_name_is_valid() -> None:
    subsets, info_size = _trimmed_lzma_base64(
        [["1", "4", "", "opaque", "opaque", "opaque", "opaque"]]
    )

    snapshot = _parse_area_set_snapshot(
        {"mid": "1", "type": "ar", "infoSize": info_size, "subsets": subsets}
    )

    assert snapshot.areas == (_AreaMetadata(area_id="4", name=""),)


@pytest.mark.parametrize(
    ("subsets", "info_size"),
    [
        ("not-base64", 1),
        ("AAAA", 1),
        _trimmed_lzma_base64("not-rows"),
        _trimmed_lzma_base64([["2", "4", "Zone", 0, 0, 0, 0]]),
        _trimmed_lzma_base64([["1", "4", "Zone"]]),
    ],
    ids=["base64", "lzma", "json", "mid-mismatch", "unknown-row"],
)
def test_getAreaSet_malformed_snapshot_fails_closed(
    event_bus_mock: Mock, subsets: str, info_size: int
) -> None:
    result = GetAreaSet.handle(
        event_bus_mock,
        _area_set_message(subsets=subsets, info_size=info_size),
    )

    assert result.state == HandlingState.ANALYSE_LOGGED
    event_bus_mock.notify.assert_not_called()


def test_getAreaSet_vw_is_known_negative_family(event_bus_mock: Mock) -> None:
    result = GetAreaSet.handle(
        event_bus_mock,
        _area_set_message(type_value="vw"),
    )

    assert result.state == HandlingState.SUCCESS
    event_bus_mock.notify.assert_not_called()


def test_coordinator_rejects_mid_and_id_set_mismatches() -> None:
    coordinator = _MowerWorkAreaCoordinator()
    assert coordinator.update_static_map(_synthetic_static_map()) is None
    assert (
        coordinator.update_geometry(_synthetic_geometry("1", directions="34")) is None
    )
    assert coordinator.update_metadata(_synthetic_metadata("2")) is None

    other = _MowerWorkAreaCoordinator()
    assert other.update_static_map(_synthetic_static_map()) is None
    assert (
        other.update_geometry(_synthetic_geometry("1", mid="2", directions="34"))
        is None
    )
    assert other.update_metadata(_synthetic_metadata("1", mid="2")) is None


def test_coordinator_replaces_snapshot_after_changed_id_set() -> None:
    coordinator = _MowerWorkAreaCoordinator()
    assert coordinator.update_static_map(_synthetic_static_map()) is None
    assert (
        coordinator.update_geometry(_synthetic_geometry("1", directions="34")) is None
    )
    first = coordinator.update_metadata(_synthetic_metadata("1", name="First"))
    assert first is not None
    assert [area.geometry.group_id for area in first.areas] == ["1"]

    assert (
        coordinator.update_geometry(_synthetic_geometry("2", directions="56")) is None
    )
    second = coordinator.update_metadata(_synthetic_metadata("2", name="Second"))
    assert second is not None
    assert [area.geometry.group_id for area in second.areas] == ["2"]


def test_registration_rejects_no_shared_run() -> None:
    assert (
        _find_registration(
            parse_rle_path("0,0", "1"),
            parse_rle_path("100,100", "2"),
        )
        is None
    )


def test_registration_rejects_ambiguous_translations() -> None:
    assert (
        _find_registration(
            parse_rle_path("0,0", "121"),
            parse_rle_path("100,100", "1"),
        )
        is None
    )


def test_registration_does_not_close_area_artificially() -> None:
    coordinator = _MowerWorkAreaCoordinator()
    coordinator.update_static_map(_synthetic_static_map(directions="123"))
    coordinator.update_geometry(_synthetic_geometry("1", directions="2"))
    event = coordinator.update_metadata(_synthetic_metadata("1"))

    assert event is not None
    points = event.areas[0].geometry.segments[0].points
    assert len(points) == 2
    assert points[0] != points[-1]


def test_work_area_fixture_digests_are_stable() -> None:
    assert hashlib.sha256(_AREA_SET["subsets"].encode()).hexdigest() == (
        "0666ffedcfc430d12409c7e2225fd0a75cb149ed6fbbb52c522ea5fde61952dd"
    )
    assert [len(chunk) for chunk in _ON_ARI["chunks"]] == [1024, 1024, 208]
