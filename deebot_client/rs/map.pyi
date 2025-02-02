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

    def generate_svg(
        self,
        viewbox: tuple[float, float, float, float],
        image: bytes,
        subsets: list[MapSubsetEvent],
        position: list[Position],
    ) -> str:
        """Generate SVG image."""

class PositionType(Enum):
    """Position type enum."""

    DEEBOT = auto()
    CHARGER = auto()

    @staticmethod
    def from_str(value: str) -> PositionType:
        """Create a position type from string."""
