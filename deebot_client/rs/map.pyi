from typing import Self

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
