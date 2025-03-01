from enum import Enum, auto
from typing import Self

from deebot_client.events.map import MapSubsetEvent, Position

class MapData:
    """Map data in rust."""

    def __new__(cls) -> Self:
        """Create a new map data object."""

    def add_trace_points(self, value: str) -> None:
        """Add trace points to the map data."""

    def clear_trace_points(self) -> None:
        """Clear trace points."""

    def update_map_piece(self, index: int, base64_data: str) -> bool:
        """Update map piece."""

    def map_piece_crc32_indicates_update(self, index: int, crc32: int) -> bool:
        """Return True if update is required."""

    def generate_svg(
        self,
        subsets: list[MapSubsetEvent],
        position: list[Position],
    ) -> str | None:
        """Generate SVG image."""

class PositionType(Enum):
    """Position type enum."""

    DEEBOT = auto()
    CHARGER = auto()

    @staticmethod
    def from_str(value: str) -> PositionType:
        """Create a position type from string."""
