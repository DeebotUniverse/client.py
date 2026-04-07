from enum import Enum, auto
from typing import Self

from deebot_client.events.map import MapSubsetEvent, Position

class BackgroundImage:
    """Background image in rust."""

    def update_map_piece(self, index: int, base64_data: str) -> bool:
        """Update a map piece."""

    def map_piece_crc32_indicates_update(self, index: int, crc32: int) -> bool:
        """Return True when the piece should be refreshed."""

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
        direction: int,
    ) -> bool:
        """Store NGIOT background metadata and encoded payload."""

    def clear(self) -> bool:
        """Clear NGIOT background metadata."""

    def has_map_data(self) -> bool:
        """Return True if NGIOT background data is present."""

class TracePoints:
    """Trace points in rust."""

    def add(self, value: str, lz4_len: int | None = None) -> None:
        """Add trace points to the trace points object."""

    def clear(self) -> None:
        """Clear trace points."""

    def use_legacy_scale(self) -> None:
        """Use legacy trace scale."""

    def use_world_scale(self) -> None:
        """Use world-space trace scale."""

class MapInfo:
    """Map info."""

    def set(self, base64_data: str) -> None:
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

    def set_map_info(self, base64_data: str) -> None:
        """Compatibility wrapper for Python map.py."""

    def set_ngiot_background(
        self,
        encoded: str,
        width: int,
        height: int,
        total_width: int,
        total_height: int,
        resolution: int,
        x_min: int,
        y_max: int,
        direction: int,
    ) -> bool:
        """Compatibility wrapper for Python map.py."""

    def clear_ngiot_background(self) -> bool:
        """Compatibility wrapper for Python map.py."""

    def has_ngiot_background(self) -> bool:
        """Compatibility wrapper for Python map.py."""

    def add_trace_points(self, value: str, lz4_len: int | None = None) -> None:
        """Compatibility wrapper for Python map.py."""

    def clear_trace_points(self) -> None:
        """Compatibility wrapper for Python map.py."""

    def use_legacy_trace_scale(self) -> None:
        """Compatibility wrapper for Python map.py."""

    def use_world_trace_scale(self) -> None:
        """Compatibility wrapper for Python map.py."""

    def use_legacy_position_icon_scale(self) -> None:
        """Use legacy position icon scale."""

    def use_ngiot_position_icon_scale(self) -> None:
        """Use NGIOT position icon scale."""

    def use_legacy_position_transform(self) -> None:
        """Use legacy position transform."""

    def use_ngiot_position_transform(self) -> None:
        """Use NGIOT position transform."""

    def generate_svg(
        self,
        subsets: list[MapSubsetEvent],
        position: list[Position],
        rotation: "RotationAngle",
    ) -> str | None:
        """Generate SVG image."""

class PositionType(Enum):
    """Position type enum."""

    DEEBOT = auto()
    CHARGER = auto()

    @staticmethod
    def from_str(value: str) -> "PositionType":
        """Create a position type from string."""

class RotationAngle(Enum):
    """Rotation angle enum."""

    DEG_0 = auto()
    DEG_90 = auto()
    DEG_180 = auto()
    DEG_270 = auto()

    @staticmethod
    def from_int(value: int) -> "RotationAngle":
        """Create a rotation angle from integer."""