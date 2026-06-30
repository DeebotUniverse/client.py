"""Mower trajectory accumulator and SVG renderer.

Mowers (e.g. Ecovacs GOAT family) do not expose the regular ``map``
capability used by vacuums, but their firmware pushes trajectory points
through :class:`~deebot_client.events.map.MapTraceEvent` (flat) and the
richer :class:`~deebot_client.events.map.MowerMapTraceEvent` (groups +
segments). This module keeps the parsing, accumulation and rendering of
those points in one place so consumers (e.g. the Home Assistant
integration) only have to forward the event payload and read back an SVG.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from deebot_client.events.map import MowerMapTraceGroup


class MowerMapTrace:
    """Accumulator and SVG renderer for mower trajectory traces."""

    MAX_POINTS = 5000

    _STROKE_COLOR = "#1976d2"

    def __init__(self) -> None:
        self._points: list[tuple[int, int]] = []

    @property
    def has_points(self) -> bool:
        """Return whether any trace points have been accumulated."""
        return bool(self._points)

    def clear(self) -> None:
        """Drop all accumulated trace points."""
        self._points.clear()

    def add_data(self, raw: str) -> int:
        """Parse a ``MapTraceEvent.data`` string and accumulate points.

        Tokens are ``"x,y"`` separated by ``";"``. Malformed tokens are
        skipped silently. The accumulator keeps at most :attr:`MAX_POINTS`
        points (FIFO drop). Returns the number of points actually added.

        This is the legacy flat path. Prefer :meth:`add_groups` for
        :class:`MowerMapTraceEvent` payloads — it preserves the segment
        boundaries that this flat representation loses.
        """
        new_points: list[tuple[int, int]] = []
        for raw_token in raw.split(";"):
            token = raw_token.strip()
            if not token:
                continue
            try:
                x_str, y_str = token.split(",")
                new_points.append((int(x_str), int(y_str)))
            except ValueError:
                continue
        return self._extend(new_points)

    def add_groups(self, groups: Iterable[MowerMapTraceGroup]) -> int:
        """Accumulate points from a structured :class:`MowerMapTraceEvent`.

        Group and segment boundaries are preserved in the source payload
        (and matter for future static-map work), but the current SVG
        renderer projects them onto a single polyline. We flatten at
        accumulation time and keep the boundaries available to richer
        renderers if/when they land.
        """
        new_points: list[tuple[int, int]] = [
            point
            for group in groups
            for segment in group.segments
            for point in segment.points
        ]
        return self._extend(new_points)

    def _extend(self, new_points: list[tuple[int, int]]) -> int:
        if not new_points:
            return 0
        self._points.extend(new_points)
        if len(self._points) > self.MAX_POINTS:
            self._points = self._points[-self.MAX_POINTS :]
        return len(new_points)

    def to_svg(self) -> str | None:
        """Render the accumulated trace as an SVG polyline.

        Returns ``None`` when no points have been accumulated yet.
        """
        if not self._points:
            return None

        xs = [p[0] for p in self._points]
        ys = [p[1] for p in self._points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # 5% padding on the larger of the two dimensions, with a 50-unit floor
        # so a near-zero-area trace still has visible margin.
        padding = max(50, max(max_x - min_x, max_y - min_y) // 20)
        min_x -= padding
        max_x += padding
        min_y -= padding
        max_y += padding

        width = max_x - min_x
        height = max_y - min_y

        # Mower coordinates use bottom-up Y; flip for SVG top-down rendering.
        flipped = " ".join(f"{x},{max_y + min_y - y}" for x, y in self._points)

        # Stroke scales with width so the line stays visible on tiny lawns
        # and isn't a hairline on huge ones.
        stroke_width = max(20, width // 200)

        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{min_x} {min_y} {width} {height}" '
            f'preserveAspectRatio="xMidYMid meet">'
            f'<polyline points="{flipped}" fill="none" '
            f'stroke="{self._STROKE_COLOR}" stroke-width="{stroke_width}" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
            f"</svg>"
        )
