from enum import Enum, auto
from typing import Self

from deebot_client.events.map import MapSubsetEvent, Position

class NgiotBackground:
    """NGIOT background placeholder."""

    def set_map_data(
        self,
        encoded: str,
        width: int,
        height: int,
        total_width: int,
        total_height: int,
        resolution: int,
        x_min: int,
        y_max: int,
    ) -> bool:
        """Store NGIOT background metadata and encoded payload."""

    def clear(self) -> bool:
        """Clear NGIOT background metadata."""

    def has_data(self) -> bool:
        """Return True if NGIOT background data is present."""

class TracePoints:
    """Trace points in rust."""

    def add(self, value: str, lz4_len: int | None = None) -> None:
        """Add trace points to the trace points object.""

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
    def ngiot_background(self) -> NgiotBackground:
        """Return NGIOT background placeholder."""

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
