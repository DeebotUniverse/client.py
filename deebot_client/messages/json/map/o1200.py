"""Shared structural helpers for the evidenced GOAT O1200 map format."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import re
from typing import Final

from deebot_client.rs.util import decompress_base64_data

OBSERVED_DIRECTION_STEP: Final = 50
OBSERVED_LZMA_PREFIX: Final = bytes.fromhex("5d00000400")
MAX_RLE_BLOCK_POINTS: Final = 4_096

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


@dataclass(frozen=True)
class O1200RlePath:
    """One strictly parsed local O1200 direction path."""

    points: tuple[tuple[int, int], ...]
    directions: tuple[str, ...]


def canonical_decimal(value: object) -> int | None:
    """Return an int only for integers or canonical decimal strings."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and _CANONICAL_DECIMAL.fullmatch(value):
        return int(value)
    return None


def parse_coordinate(value: str) -> tuple[int, int]:
    """Parse one strict integer coordinate pair."""
    match = _COORDINATE.fullmatch(value)
    if match is None:
        raise ValueError("Unsupported O1200 coordinate")
    return int(match[1]), int(match[2])


def strict_base64_decode(value: str) -> bytes:
    """Decode strict canonical Base64 without accepting alternate spellings."""
    encoded = value.encode("ascii")
    if len(encoded) % 4:
        raise ValueError("Base64 length is not canonical")
    decoded = base64.b64decode(encoded, validate=True)
    if base64.b64encode(decoded) != encoded:
        raise ValueError("Base64 representation is not canonical")
    return decoded


def decode_trimmed_lzma(value: str, *, info_size: int) -> bytes:
    """Decode one canonical Base64 trimmed LZMA-Alone representation."""
    compressed = strict_base64_decode(value)
    return decode_trimmed_lzma_bytes(compressed, info_size=info_size)


def decode_trimmed_lzma_bytes(compressed: bytes, *, info_size: int) -> bytes:
    """Decode validated trimmed LZMA-Alone bytes with an expected output size."""
    if (
        info_size <= 0
        or len(compressed) < 9
        or compressed[:5] != OBSERVED_LZMA_PREFIX
        or int.from_bytes(compressed[5:9], "little") != info_size
    ):
        raise ValueError("Unsupported trimmed LZMA-Alone framing")

    decoded = decompress_base64_data(base64.b64encode(compressed).decode("ascii"))
    if len(decoded) != info_size:
        raise ValueError("Decoded length does not match infoSize")
    return decoded


def parse_rle_path(start: str, encoded_rle: str) -> O1200RlePath:
    """Expand one observed O1200 RLE path, preserving its direction sequence."""
    points: list[tuple[int, int]] = [parse_coordinate(start)]
    directions: list[str] = []
    position = 0
    for match in _RLE_TOKEN.finditer(encoded_rle):
        if match.start() != position:
            raise ValueError("Unsupported O1200 RLE token")
        position = match.end()
        repeat = int(match[2] or "1")
        if len(points) + repeat > MAX_RLE_BLOCK_POINTS:
            raise ValueError("O1200 RLE point limit exceeded")
        direction = match[1]
        directions.extend([direction] * repeat)
        dx, dy = _DIRECTIONS[direction]
        for _ in range(repeat):
            previous_x, previous_y = points[-1]
            points.append(
                (
                    previous_x + dx * OBSERVED_DIRECTION_STEP,
                    previous_y + dy * OBSERVED_DIRECTION_STEP,
                )
            )

    if position != len(encoded_rle) or not directions:
        raise ValueError("Unsupported O1200 RLE path")
    return O1200RlePath(points=tuple(points), directions=tuple(directions))
