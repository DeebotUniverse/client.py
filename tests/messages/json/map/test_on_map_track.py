from __future__ import annotations

import base64
from typing import Any
from unittest.mock import Mock, call

import pytest

from deebot_client.event_bus import EventBus
from deebot_client.events.map import (
    MowerMapTrackEvent,
    MowerMapTrackRecord,
    MowerMapTrackSegment,
)
from deebot_client.message import HandlingState
from deebot_client.messages import get_message
from deebot_client.messages.json.map.map_track import OnMapTrack, _reset_map_track_state
from tests import get_static_device_info
from tests.fixtures.goat_map_track import (
    COMPLETION_LIKE_RESIDUAL,
    FULL_SNAPSHOT,
    OUTER_TWO_UPDATES,
    PATCH_ADD,
    PATCH_DELETE,
    PATCH_REPLACE,
    REAL_P2_16B_INITIAL_FULL_WITH_KEY_ONLY,
    REAL_P2_16B_PATCH_KEY_ONLY_DELETE,
    UNKNOWN_PROTOCOL,
    UNKNOWN_UPDATE_TYPE,
    chunked_messages,
    trimmed_lzma,
)


@pytest.fixture(autouse=True)
def reset_map_track_state() -> None:
    _reset_map_track_state()


def _event_bus() -> Mock:
    event_bus = Mock(spec_set=EventBus)
    static_device_info = get_static_device_info("2i0fns")
    assert static_device_info is not None
    event_bus.capabilities = static_device_info.capabilities
    return event_bus


def _handle(event_bus: Mock, payload: dict[str, Any]) -> HandlingState:
    return OnMapTrack.handle(event_bus, payload).state


def _records(
    event: MowerMapTrackEvent,
) -> dict[tuple[str, str, str], MowerMapTrackRecord]:
    return {record.key: record for record in event.records}


def _points(record: MowerMapTrackRecord) -> tuple[tuple[int, int], ...]:
    return tuple(point for segment in record.segments for point in segment.points)


def test_get_message_registers_on_map_track_for_goat() -> None:
    static_device_info = get_static_device_info("2i0fns")
    assert static_device_info is not None
    assert get_message("onMapTrack", static_device_info) is OnMapTrack


def test_single_chunk_full_snapshot_publishes_current_state() -> None:
    event_bus = _event_bus()
    payload = chunked_messages(FULL_SNAPSHOT, batid="fixture-full")[0]

    assert _handle(event_bus, payload) == HandlingState.SUCCESS

    event_bus.notify.assert_called_once()
    event = event_bus.notify.call_args.args[0]
    assert event == MowerMapTrackEvent(
        mid="0",
        protocol_version="1",
        update_type=1,
        step_size=50,
        records=(
            MowerMapTrackRecord(
                key=("1", "1", "100"),
                raw="1;1;100;0,0;100,0",
                segments=(MowerMapTrackSegment(points=((0, 0), (100, 0))),),
                geometry_encoding="points",
            ),
            MowerMapTrackRecord(
                key=("1", "2", "0"),
                raw="1;2;0;550,-2400;2(2)",
                segments=(
                    MowerMapTrackSegment(
                        points=((550, -2400), (600, -2450), (650, -2500))
                    ),
                ),
                geometry_encoding="rle",
            ),
        ),
    )


def test_out_of_order_multi_chunk_full_snapshot_is_buffered_until_complete() -> None:
    event_bus = _event_bus()
    chunks = chunked_messages(FULL_SNAPSHOT, batid="fixture-multi", chunks=3)

    assert _handle(event_bus, chunks[2]) == HandlingState.SUCCESS
    assert _handle(event_bus, chunks[0]) == HandlingState.SUCCESS
    event_bus.notify.assert_not_called()

    assert _handle(event_bus, chunks[1]) == HandlingState.SUCCESS

    event_bus.notify.assert_called_once()


def test_identical_batch_ids_are_isolated_per_event_bus_lifecycle() -> None:
    event_bus_a = _event_bus()
    event_bus_b = _event_bus()
    document_a = [["1", "1", "1;1;100;0,0;100,0"]]
    document_b = [["1", "1", "1;1;200;0,0;200,0"]]
    chunks_a = chunked_messages(document_a, batid="same-id", chunks=2)
    chunks_b = chunked_messages(document_b, batid="same-id", chunks=2)
    assert (
        chunks_a[0]["body"]["data"]["infoSize"]
        == chunks_b[0]["body"]["data"]["infoSize"]
    )

    assert _handle(event_bus_a, chunks_a[0]) == HandlingState.SUCCESS
    assert _handle(event_bus_b, chunks_b[0]) == HandlingState.SUCCESS
    assert _handle(event_bus_a, chunks_a[1]) == HandlingState.SUCCESS
    assert _handle(event_bus_b, chunks_b[1]) == HandlingState.SUCCESS

    records_a = _records(event_bus_a.notify.call_args.args[0])
    records_b = _records(event_bus_b.notify.call_args.args[0])
    assert sorted(records_a) == [("1", "1", "100")]
    assert sorted(records_b) == [("1", "1", "200")]


def test_startup_patch_does_not_establish_partial_state() -> None:
    event_bus = _event_bus()

    assert (
        _handle(event_bus, chunked_messages(PATCH_ADD, batid="fixture-patch-only")[0])
        == HandlingState.SUCCESS
    )

    event_bus.notify.assert_not_called()


def test_startup_full_snapshot_initializes_state() -> None:
    event_bus = _event_bus()

    assert (
        _handle(event_bus, chunked_messages(FULL_SNAPSHOT, batid="fixture-full")[0])
        == HandlingState.SUCCESS
    )

    event_bus.notify.assert_called_once()


def test_full_patch_replace_and_key_only_delete_replay_state() -> None:
    event_bus = _event_bus()

    for payload in chunked_messages(FULL_SNAPSHOT, batid="fixture-seq-full"):
        assert _handle(event_bus, payload) == HandlingState.SUCCESS
    for payload in chunked_messages(PATCH_ADD, batid="fixture-seq-add"):
        assert _handle(event_bus, payload) == HandlingState.SUCCESS
    for payload in chunked_messages(PATCH_REPLACE, batid="fixture-seq-replace"):
        assert _handle(event_bus, payload) == HandlingState.SUCCESS
    for payload in chunked_messages(PATCH_DELETE, batid="fixture-seq-delete"):
        assert _handle(event_bus, payload) == HandlingState.SUCCESS

    assert event_bus.notify.call_count == 4
    final_event = event_bus.notify.call_args.args[0]
    records = _records(final_event)
    assert sorted(records) == [("1", "1", "101"), ("1", "2", "0")]
    assert _points(records[("1", "1", "101")]) == ((0, 100), (100, 100))


def test_full_snapshot_replaces_existing_state() -> None:
    event_bus = _event_bus()

    for payload in chunked_messages(FULL_SNAPSHOT, batid="fixture-replace-full-1"):
        assert _handle(event_bus, payload) == HandlingState.SUCCESS
    replacement = [["1", "1", "9;1;1;10,10;20,20"]]
    for payload in chunked_messages(replacement, batid="fixture-replace-full-2"):
        assert _handle(event_bus, payload) == HandlingState.SUCCESS

    final_event = event_bus.notify.call_args.args[0]
    assert tuple(record.key for record in final_event.records) == (("9", "1", "1"),)


def test_corrupt_full_then_patch_still_has_no_state() -> None:
    event_bus = _event_bus()

    assert (
        _handle(
            event_bus, chunked_messages(UNKNOWN_PROTOCOL, batid="fixture-bad-full")[0]
        )
        == HandlingState.ANALYSE_LOGGED
    )
    assert (
        _handle(event_bus, chunked_messages(PATCH_ADD, batid="fixture-after-bad")[0])
        == HandlingState.SUCCESS
    )

    event_bus.notify.assert_not_called()


def test_full_then_corrupt_patch_preserves_previous_state() -> None:
    event_bus = _event_bus()
    corrupt_patch = [["1", "2", "1;1;100;bad-rle"]]

    assert (
        _handle(event_bus, chunked_messages(FULL_SNAPSHOT, batid="fixture-good")[0])
        == HandlingState.SUCCESS
    )
    assert (
        _handle(
            event_bus, chunked_messages(corrupt_patch, batid="fixture-bad-patch")[0]
        )
        == HandlingState.ANALYSE_LOGGED
    )

    event_bus.notify.assert_called_once()
    records = _records(event_bus.notify.call_args.args[0])
    assert sorted(records) == [("1", "1", "100"), ("1", "2", "0")]


def test_new_event_bus_lifecycle_patch_does_not_inherit_old_state() -> None:
    event_bus_a = _event_bus()
    event_bus_b = _event_bus()

    assert (
        _handle(event_bus_a, chunked_messages(FULL_SNAPSHOT, batid="fixture-old")[0])
        == HandlingState.SUCCESS
    )
    assert (
        _handle(event_bus_b, chunked_messages(PATCH_REPLACE, batid="fixture-new")[0])
        == HandlingState.SUCCESS
    )

    event_bus_b.notify.assert_not_called()


def test_multiple_outer_updates_publish_after_full_batch_validation() -> None:
    event_bus = _event_bus()

    assert (
        _handle(
            event_bus, chunked_messages(OUTER_TWO_UPDATES, batid="fixture-outer")[0]
        )
        == HandlingState.SUCCESS
    )

    first, second = [item.args[0] for item in event_bus.notify.call_args_list]
    assert first.update_type == 1
    assert _points(_records(first)[("1", "1", "100")]) == ((0, 0), (100, 0))
    assert second.update_type == 2
    assert _points(_records(second)[("1", "1", "100")]) == ((0, 0), (150, 0))


def test_malformed_later_outer_update_does_not_publish_or_mutate() -> None:
    event_bus = _event_bus()
    document = [
        ["1", "1", "1;1;100;0,0;100,0"],
        ["1", "2", "1;1;100;bad-rle"],
    ]

    assert (
        _handle(event_bus, chunked_messages(document, batid="fixture-atomic-bad")[0])
        == HandlingState.ANALYSE_LOGGED
    )
    assert (
        _handle(
            event_bus, chunked_messages(PATCH_REPLACE, batid="fixture-after-atomic")[0]
        )
        == HandlingState.SUCCESS
    )

    event_bus.notify.assert_not_called()


def test_incomplete_batch_does_not_publish() -> None:
    event_bus = _event_bus()
    chunks = chunked_messages(FULL_SNAPSHOT, batid="fixture-incomplete", chunks=2)

    assert _handle(event_bus, chunks[0]) == HandlingState.SUCCESS

    event_bus.notify.assert_not_called()


def test_duplicate_chunk_is_classified_as_analyse_without_corrupting_later_state() -> (
    None
):
    event_bus = _event_bus()
    chunks = chunked_messages(FULL_SNAPSHOT, batid="fixture-duplicate", chunks=2)

    assert _handle(event_bus, chunks[0]) == HandlingState.SUCCESS
    assert _handle(event_bus, chunks[0]) == HandlingState.ANALYSE_LOGGED
    event_bus.notify.assert_not_called()

    assert (
        _handle(
            event_bus,
            chunked_messages(FULL_SNAPSHOT, batid="fixture-after-duplicate")[0],
        )
        == HandlingState.SUCCESS
    )
    event_bus.notify.assert_called_once()


@pytest.mark.parametrize(
    "payload",
    [
        {
            "body": {
                "data": {
                    "mid": "0",
                    "batid": "bad",
                    "serial": "01",
                    "index": "0",
                    "infoSize": 1,
                    "info": "AA==",
                }
            }
        },
        {
            "body": {
                "data": {
                    "mid": "0",
                    "batid": "bad",
                    "serial": "1",
                    "index": "0",
                    "infoSize": 1,
                    "info": "not-base64",
                }
            }
        },
        {
            "body": {
                "data": {
                    "mid": "0",
                    "batid": "bad",
                    "serial": "1",
                    "index": "0",
                    "infoSize": 1,
                    "info": "AA==",
                }
            }
        },
    ],
)
def test_malformed_segment_is_analyse_logged(payload: dict[str, Any]) -> None:
    event_bus = _event_bus()

    assert _handle(event_bus, payload) == HandlingState.ANALYSE_LOGGED
    event_bus.notify.assert_not_called()


@pytest.mark.parametrize("document", [UNKNOWN_PROTOCOL, UNKNOWN_UPDATE_TYPE])
def test_unsupported_protocol_or_update_type_preserves_previous_state(
    document: list[list[str]],
) -> None:
    event_bus = _event_bus()

    assert (
        _handle(event_bus, chunked_messages(FULL_SNAPSHOT, batid="fixture-good")[0])
        == HandlingState.SUCCESS
    )
    assert (
        _handle(event_bus, chunked_messages(document, batid="fixture-bad")[0])
        == HandlingState.ANALYSE_LOGGED
    )

    event_bus.notify.assert_called_once()


def test_infosize_mismatch_is_analyse_logged() -> None:
    event_bus = _event_bus()
    info, info_size = trimmed_lzma(FULL_SNAPSHOT)

    payload = {
        "body": {
            "data": {
                "mid": "0",
                "batid": "fixture-size-mismatch",
                "serial": "1",
                "index": "0",
                "infoSize": info_size + 1,
                "info": info,
            }
        }
    }

    assert _handle(event_bus, payload) == HandlingState.ANALYSE_LOGGED
    event_bus.notify.assert_not_called()


def test_noncanonical_base64_is_rejected() -> None:
    event_bus = _event_bus()
    info, info_size = trimmed_lzma(FULL_SNAPSHOT)
    noncanonical = (
        base64.b64encode(base64.b64decode(info, validate=True)).decode() + "A"
    )

    payload = {
        "body": {
            "data": {
                "mid": "0",
                "batid": "fixture-noncanonical",
                "serial": "1",
                "index": "0",
                "infoSize": info_size,
                "info": noncanonical,
            }
        }
    }

    assert _handle(event_bus, payload) == HandlingState.ANALYSE_LOGGED
    event_bus.notify.assert_not_called()


def test_completion_like_residual_state_keeps_geometry_and_applies_key_only_delete() -> (
    None
):
    event_bus = _event_bus()

    assert (
        _handle(
            event_bus,
            chunked_messages(COMPLETION_LIKE_RESIDUAL, batid="fixture-residual")[0],
        )
        == HandlingState.SUCCESS
    )

    assert event_bus.notify.call_count == 2
    final_event = event_bus.notify.call_args.args[0]
    records = _records(final_event)
    assert ("1", "1", "311") not in records
    assert sorted(records) == [
        ("1", "1", "312"),
        ("1", "1", "322"),
        ("1", "1", "324"),
        ("1", "2", "0"),
    ]
    assert _points(records[("1", "2", "0")]) == (
        (550, -2400),
        (600, -2450),
        (650, -2500),
        (700, -2550),
        (750, -2600),
    )


def test_real_p2_16b_full_snapshot_omits_key_only_records() -> None:
    event_bus = _event_bus()

    for payload in REAL_P2_16B_INITIAL_FULL_WITH_KEY_ONLY:
        assert _handle(event_bus, payload) == HandlingState.SUCCESS

    event = event_bus.notify.call_args.args[0]
    records = _records(event)
    assert len(records) == 139
    assert ("1", "1", "325") not in records
    assert ("1", "1", "326") not in records
    assert ("1", "1", "327") not in records
    assert ("1", "1", "328") not in records


def test_real_p2_16b_patch_key_only_delete_removes_existing_record() -> None:
    event_bus = _event_bus()

    for payload in chunked_messages([["1", "1", "1;1;306;0,0;100,0"]], batid="seed"):
        assert _handle(event_bus, payload) == HandlingState.SUCCESS
    for payload in REAL_P2_16B_PATCH_KEY_ONLY_DELETE:
        assert _handle(event_bus, payload) == HandlingState.SUCCESS

    assert ("1", "1", "306") not in _records(event_bus.notify.call_args.args[0])


def test_mixed_direct_and_rle_geometry_preserves_segment_boundaries() -> None:
    event_bus = _event_bus()
    record = "1;2;0;850,400;900,1050;676(2)7(2)8(8)1;900,400;950,1100;300,850;950,1150;"

    assert (
        _handle(
            event_bus, chunked_messages([["1", "1", record]], batid="fixture-mixed")[0]
        )
        == HandlingState.SUCCESS
    )

    parsed = event_bus.notify.call_args.args[0].records[0]
    assert parsed.geometry_encoding == "rle"
    assert len(parsed.segments) == 2
    assert parsed.segments[0].points[0:2] == ((850, 400), (900, 1050))
    assert parsed.segments[1].points == (
        (900, 400),
        (950, 1100),
        (300, 850),
        (950, 1150),
    )


def test_multi_segment_rle_record_preserves_segment_boundaries() -> None:
    event_bus = _event_bus()
    document = [["1", "1", "1;2;0;0,0;1(2);100,100;5(2)"]]

    assert (
        _handle(event_bus, chunked_messages(document, batid="fixture-multi-rle")[0])
        == HandlingState.SUCCESS
    )

    record = event_bus.notify.call_args.args[0].records[0]
    assert record.geometry_encoding == "rle"
    assert record.segments == (
        MowerMapTrackSegment(points=((0, 0), (50, 0), (100, 0))),
        MowerMapTrackSegment(points=((100, 100), (50, 100), (0, 100))),
    )


def test_record_point_budget_rejects_many_legal_rle_blocks_without_partial_state() -> (
    None
):
    event_bus = _event_bus()
    fields = []
    for index in range(5):
        fields.extend([f"{index},0", "1(1000)"])
    too_large_record = "1;2;0;" + ";".join(fields)

    assert (
        _handle(
            event_bus,
            chunked_messages([["1", "1", too_large_record]], batid="big-record")[0],
        )
        == HandlingState.ANALYSE_LOGGED
    )

    event_bus.notify.assert_not_called()


def test_update_point_budget_rejects_many_legal_records_without_partial_state() -> None:
    event_bus = _event_bus()
    records = [f"1;2;{index};{index},0;1(4095)" for index in range(5)]

    assert (
        _handle(
            event_bus, chunked_messages([["1", "1", *records]], batid="big-update")[0]
        )
        == HandlingState.ANALYSE_LOGGED
    )

    event_bus.notify.assert_not_called()


def test_events_keep_deterministic_key_order() -> None:
    event_bus = _event_bus()
    document = [["1", "1", "2;1;10;0,0;1,1", "1;2;0;0,0;1", "1;1;9;0,0;1,1"]]

    assert (
        _handle(event_bus, chunked_messages(document, batid="fixture-order")[0])
        == HandlingState.SUCCESS
    )

    event = event_bus.notify.call_args.args[0]
    assert [record.key for record in event.records] == [
        ("1", "1", "9"),
        ("1", "2", "0"),
        ("2", "1", "10"),
    ]


def test_no_extra_events_are_published_for_initialized_single_update() -> None:
    event_bus = _event_bus()

    assert (
        _handle(event_bus, chunked_messages(FULL_SNAPSHOT, batid="fixture-seed")[0])
        == HandlingState.SUCCESS
    )
    assert (
        _handle(event_bus, chunked_messages(PATCH_ADD, batid="fixture-patch")[0])
        == HandlingState.SUCCESS
    )

    event_bus.notify.assert_has_calls(
        [
            call(
                MowerMapTrackEvent(
                    mid="0",
                    protocol_version="1",
                    update_type=2,
                    records=(
                        MowerMapTrackRecord(
                            key=("1", "1", "100"),
                            raw="1;1;100;0,0;100,0",
                            segments=(MowerMapTrackSegment(points=((0, 0), (100, 0))),),
                            geometry_encoding="points",
                        ),
                        MowerMapTrackRecord(
                            key=("1", "1", "101"),
                            raw="1;1;101;0,100;100,100",
                            segments=(
                                MowerMapTrackSegment(points=((0, 100), (100, 100))),
                            ),
                            geometry_encoding="points",
                        ),
                        MowerMapTrackRecord(
                            key=("1", "2", "0"),
                            raw="1;2;0;550,-2400;2(2)",
                            segments=(
                                MowerMapTrackSegment(
                                    points=((550, -2400), (600, -2450), (650, -2500))
                                ),
                            ),
                            geometry_encoding="rle",
                        ),
                    ),
                    step_size=50,
                )
            )
        ]
    )
