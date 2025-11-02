from enum import Enum, auto
from typing import Self

from deebot_client.events.map import MapSubsetEvent, Position

class BackgroundImage:
    """Map background image."""

    def update_map_piece(self, index: int, base64_data: str) -> bool:
        """Update map piece."""

    def map_piece_crc32_indicates_update(self, index: int, crc32: int) -> bool:
        """Return True if update is required."""

class TracePoints:
    """Trace points in rust."""

    def add(self, value: str) -> None:
        """Add trace points to the trace points object."""

    def clear(self) -> None:
        """Clear all trace points."""

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
