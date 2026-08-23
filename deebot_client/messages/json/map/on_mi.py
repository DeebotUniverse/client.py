"""GOAT static-map message handling."""

from __future__ import annotations

import base64
import binascii
import re
from typing import TYPE_CHECKING, Any, Final

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
from deebot_client.rs.util import decompress_base64_data

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_OBSERVED_DIRECTION_STEP: Final = 50
_OBSERVED_LZMA_PREFIX: Final = bytes.fromhex("5d00000400")
_MAX_GEOMETRY_POINTS: Final = 100_000
_CANONICAL_DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)\Z")
_COORDINATE = re.compile(r"(-?(?:0|[1-9][0-9]*)),(-?(?:0|[1-9][0-9]*))\Z")
_RLE_TOKEN = re.compile(r"([1-8])(?:\(([1-9][0-9]*)\))?")
_DIRECTIONS: Final = {
    "1": (1, 0),
    "2": (1, -1),
    "3": (0, -1),
    "4": (-1, -1),
    "5": (-1, 0),
    "6": (-1, 1),
    "7": (0, 1),
    "8": (1, 1),
}


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
        return HandlingResult.success()


def _analyse_without_payload_log() -> HandlingResult:
    """Fall through without logging the complete device envelope."""
    return HandlingResult(HandlingState.ANALYSE_LOGGED)


def _parse_static_map(  # noqa: PLR0911 - fail-closed validation is clearest as guard clauses
    data: dict[str, Any],
) -> MowerStaticMapEvent | None:
    """Parse one validated, first-segment GOAT static-map representation."""
    mid = data.get("mid")
    if not isinstance(mid, str) or not mid:
        return None
    if _canonical_decimal(data.get("index")) != 0:
        return None

    info_size = _canonical_decimal(data.get("infoSize"))
    if info_size is None or info_size <= 0:
        return None

    info = data.get("info")
    if not isinstance(info, str):
        return None
    compressed = _strict_base64_decode(info)
    if len(compressed) < 9 or compressed[:5] != _OBSERVED_LZMA_PREFIX:
        return None

    # The observed representation retains all four low size bytes at offsets
    # 5..8. The shared helper restores the missing four high bytes at position 9.
    if int.from_bytes(compressed[5:9], "little") != info_size:
        return None

    decoded_bytes = decompress_base64_data(info)
    if len(decoded_bytes) != info_size:
        return None

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
        step_size=_OBSERVED_DIRECTION_STEP,
    )


def _canonical_decimal(value: object) -> int | None:
    """Return an int only for integers or canonical decimal strings."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and _CANONICAL_DECIMAL.fullmatch(value):
        return int(value)
    return None


def _strict_base64_decode(value: str) -> bytes:
    """Decode strict canonical Base64 without accepting alternate spellings."""
    encoded = value.encode("ascii")
    if len(encoded) % 4:
        raise ValueError("Base64 length is not canonical")
    decoded = base64.b64decode(encoded, validate=True)
    if base64.b64encode(decoded) != encoded:
        raise ValueError("Base64 representation is not canonical")
    return decoded


def _is_string_record(value: object, expected_id: str) -> bool:
    """Check the observed JSON record container shape."""
    return (
        isinstance(value, list)
        and bool(value)
        and value[0] == expected_id
        and all(isinstance(item, str) for item in value)
    )


def _parse_geometry_segment(  # noqa: PLR0911 - malformed shapes fail closed
    raw: str, *, expected_mid: str
) -> MowerMapTraceSegment | None:
    """Expand one evidenced s1 RLE segment while preserving its raw form."""
    try:
        object_id, segment_mid, start, encoded_rle = raw.split(";", 3)
    except ValueError:
        return None
    if object_id != "s1" or segment_mid != expected_mid or not encoded_rle:
        return None

    coordinate_match = _COORDINATE.fullmatch(start)
    if coordinate_match is None:
        return None
    points = [(int(coordinate_match[1]), int(coordinate_match[2]))]

    position = 0
    for match in _RLE_TOKEN.finditer(encoded_rle):
        if match.start() != position:
            return None
        position = match.end()
        repeat = int(match[2] or "1")
        if len(points) + repeat > _MAX_GEOMETRY_POINTS:
            return None
        dx, dy = _DIRECTIONS[match[1]]
        for _ in range(repeat):
            previous_x, previous_y = points[-1]
            points.append(
                (
                    previous_x + dx * _OBSERVED_DIRECTION_STEP,
                    previous_y + dy * _OBSERVED_DIRECTION_STEP,
                )
            )

    if position != len(encoded_rle) or len(points) == 1:
        return None
    return MowerMapTraceSegment(points=points, raw=raw)
