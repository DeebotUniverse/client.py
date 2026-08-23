"""GOAT static-map message handling."""

from __future__ import annotations

import binascii
from typing import TYPE_CHECKING, Any

import orjson

from deebot_client.events.map import (
    MowerMapTraceGroup,
    MowerMapTraceSegment,
    MowerStaticMapEvent,
)
from deebot_client.message import (
    HandlingResult,
    HandlingState,
    MessageBodyDataDict,
)

from .o1200 import (
    OBSERVED_DIRECTION_STEP,
    canonical_decimal,
    decode_trimmed_lzma,
    parse_rle_path,
    strict_base64_decode,
)

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_strict_base64_decode = strict_base64_decode


class OnMI(MessageBodyDataDict):
    """Parse the evidenced GOAT static main-map representation."""

    NAME = "onMI"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Emit static geometry only for a fully validated representation."""
        try:
            event = _parse_static_map(data)
        except (
            binascii.Error,
            orjson.JSONDecodeError,
            RuntimeError,
            TypeError,
            UnicodeEncodeError,
            ValueError,
        ):
            return _analyse_without_payload_log()

        if event is None:
            return _analyse_without_payload_log()

        event_bus.notify(event)

        # Import lazily to keep the static parser independent from the
        # work-area message module while still updating the shared snapshot.
        from .work_areas import update_static_map_snapshot  # noqa: PLC0415

        update_static_map_snapshot(event_bus, event)
        return HandlingResult.success()


def _analyse_without_payload_log() -> HandlingResult:
    """Fall through without recording the complete device envelope."""
    return HandlingResult(HandlingState.ANALYSE_LOGGED)


def _parse_static_map(  # noqa: PLR0911 - fail-closed validation is clearest as guard clauses
    data: dict[str, Any],
) -> MowerStaticMapEvent | None:
    """Parse one validated, first-segment GOAT static-map representation."""
    mid = data.get("mid")
    if not isinstance(mid, str) or not mid:
        return None
    if canonical_decimal(data.get("index")) != 0:
        return None

    info_size = canonical_decimal(data.get("infoSize"))
    if info_size is None or info_size <= 0:
        return None

    info = data.get("info")
    if not isinstance(info, str):
        return None
    decoded_bytes = decode_trimmed_lzma(info, info_size=info_size)

    decoded = orjson.loads(decoded_bytes)
    if not isinstance(decoded, list):
        return None

    # Both evidenced forms use exactly these two opaque records. The cadence
    # form reaches this point but its empty s1 segment intentionally produces
    # no geometry event.
    if (
        len(decoded) != 2
        or not _is_string_record(decoded[0], "1")
        or not _is_string_record(decoded[1], "2")
        or len(decoded[0]) != 2
        or len(decoded[1]) != 2
    ):
        return None

    raw_segment = decoded[0][1]
    if raw_segment == "s1;0;":
        return None

    segment = _parse_geometry_segment(raw_segment, expected_mid=mid)
    if segment is None:
        return None

    return MowerStaticMapEvent(
        mid=mid,
        groups=[MowerMapTraceGroup(group_id="1", segments=[segment])],
        step_size=OBSERVED_DIRECTION_STEP,
    )


def _is_string_record(value: object, expected_id: str) -> bool:
    """Check the observed JSON record container shape."""
    return (
        isinstance(value, list)
        and bool(value)
        and value[0] == expected_id
        and all(isinstance(item, str) for item in value)
    )


def _parse_geometry_segment(
    raw: str, *, expected_mid: str
) -> MowerMapTraceSegment | None:
    """Expand one evidenced s1 RLE segment while preserving its raw form."""
    try:
        object_id, segment_mid, start, encoded_rle = raw.split(";", 3)
    except ValueError:
        return None
    if object_id != "s1" or segment_mid != expected_mid or not encoded_rle:
        return None

    try:
        path = parse_rle_path(start, encoded_rle)
    except ValueError:
        return None
    return MowerMapTraceSegment(points=path.points, raw=raw)
