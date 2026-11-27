from enum import Enum, auto
from typing import Self

from deebot_client.events.map import MapSubsetEvent, Position

class BackgroundImage:
    """Map background image."""

    def __new__(cls) -> Self:
        """Create a new background image object."""

    def update_map_piece(self, index: int, base64_data: str) -> bool:
        """Update map piece."""

    def map_piece_crc32_indicates_update(self, index: int, crc32: int) -> bool:
        """Return True if update is required."""

    def set_native_raster(
        self,
        base64_lz4: str,
        width: int,
        height: int,
        x_min: int,
        y_max: int,
        resolution: int,
    ) -> bool:
        """Set native whole-raster from raw LZ4 payload.

        Only resolution 5 (Y1 5cm cells) accepted. Extents validated with
        checked i16 arithmetic before any mutation. Raises ValueError on
        malformed payload, invalid dimensions, unsupported resolution,
        extent overflow, oversized input, or decompression error.
        """

class TracePoints:
    """Trace points in rust."""

    def __new__(cls) -> Self:
        """Create a new trace points object."""

    def add(self, value: str) -> None:
        """Add trace points to the trace points object."""

    def clear(self) -> None:
        """Clear all trace points."""

    def set_native(
        self,
        base64_lz4: str | None,
        capacity: int,
        start: int,
        total: int,
    ) -> bool:
        """Set native trace points from raw LZ4 chunk.

        Atomic: failed chunk leaves prior trace intact, no pre-clear needed.
        Total bounded by 128000 points (640000/5). Chunk must fit declared
        total (chunk_len <= total - start). Raises ValueError on cursor gap,
        ceiling overflow, malformed chunk, or decompression error.
        """

class MapInfo:
    """Map info."""

    def set(self, baset64_data: str) -> None:
        """Set map info (base64-compressed JSON)."""

class MapData:
    """Map data in rust."""

    def __new__(cls) -> Self:
        """Create a new map data object."""

    @property
    def background_image(self) -> BackgroundImage:
        """Return background image."""

    @property
    def map_info(self) -> MapInfo:
        """Return map info."""

    @property
    def trace_points(self) -> TracePoints:
        """Return trace points."""

    def generate_svg(
        self,
        subsets: list[MapSubsetEvent],
        position: list[Position],
        rotation: RotationAngle,
    ) -> str | None:
        """Generate SVG image."""

class PositionType(Enum):
    """Position type enum."""

    DEEBOT = auto()
    CHARGER = auto()

    @staticmethod
    def from_str(value: str) -> PositionType:
        """Create a position type from string."""

class RotationAngle(Enum):
    """Rotation angle enum."""

    DEG_0 = auto()
    DEG_90 = auto()
    DEG_180 = auto()
    DEG_270 = auto()

    @staticmethod
    def from_int(value: int) -> RotationAngle:
        """Create a rotation angle from integer."""
