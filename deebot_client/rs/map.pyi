from typing import Self

from deebot_client.events.map import MapSubsetEvent, Position

class TracePoint:
    """Trace point."""

    def __new__(cls, x: float, y: float, connected: bool) -> Self:
        """Create a new trace point."""

    @property
    def x(self) -> float:
        """X coordinate."""

    @property
    def y(self) -> float:
        """Y coordinate."""

    @property
    def connected(self) -> float:
        """If the point is connected."""

def extract_trace_points(value: str) -> list[TracePoint]:
    """Extract trace points from 7z compressed data string."""

class Svg:
    """SVG in rust."""

    def __new__(
        cls,
        viewbox: tuple[float, float, float, float],
        image: bytes,
        trace_points: list[TracePoint],
        subsets: list[MapSubsetEvent],
        position: list[Position],
    ) -> Self:
        """Create a new Svg object."""

    def generate(self) -> str:
        """Generate SVG image."""
