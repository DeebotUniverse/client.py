"""Map module."""
import ast
import asyncio
import base64
from collections.abc import Callable, Coroutine, Sequence
import dataclasses
from datetime import UTC, datetime
from io import BytesIO
import itertools
import lzma
import re
import struct
from textwrap import dedent
from typing import Any, Final
import zlib

from numpy import float64, reshape, zeros
from numpy.typing import NDArray
from PIL import Image, ImageDraw
import svg

from deebot_client.events.map import MapChangedEvent

from .command import Command
from .commands.json import GetCachedMapInfo, GetMinorMap
from .event_bus import EventBus
from .events import (
    MajorMapEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
    Position,
    PositionsEvent,
    PositionType,
    RoomsEvent,
)
from .exceptions import MapError
from .logging_filter import get_logger
from .models import Room
from .util import OnChangedDict, OnChangedList, cancel, create_task

_LOGGER = get_logger(__name__)
_PIXEL_WIDTH = 50

_POSITIONS_SVG_ORDER = {
    PositionType.DEEBOT: 0,
    PositionType.CHARGER: 1,
}

_SVG_MAP_MARGIN = 5

# Categorigal palette for 12 non related elements
_ROOM_COLORS = [
    "#a6cee3",
    "#1f78b4",
    "#b2df8a",
    "#33a02c",
    "#fb9a99",
    "#e31a1c",
    "#fdbf6f",
    "#ff7f00",
    "#cab2d6",
    "#6a3d9a",
    "#ffff99",
    "#b15928",
]

_OFFSET = 400
_TRACE_MAP = "trace_map"
_COLORS = {
    0x01: "#badaff",  # floor
    0x02: "#4e96e2",  # wall
    0x03: "#1a81ed",  # carpet
    _TRACE_MAP: "#FFFFFF",
    MapSetType.VIRTUAL_WALLS: "#FF0000",
    MapSetType.NO_MOP_ZONES: "#FFA500",
}

# SVG definitions referred by map elements
_SVG_DEFS = svg.Defs(
    text=dedent(
        f"""
            <!-- Gradient used by Bot icon -->
            <radialGradient id="device_bg" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
                <stop offset="70%" style="stop-color:#0000FF;"/>
                <stop offset="97%" style="stop-color:#0000FF00;"/>
            </radialGradient>

            <!-- Bot circular icon -->
            <g id="position_{PositionType.DEEBOT}">
                <circle r="5" fill="url(#device_bg)"/>
                <circle r="3.5" stroke="white" fill="blue" stroke-width="0.5"/>
            </g>

            <!-- Charger pin icon (pre-flipped vertically) -->
            <g id="position_{PositionType.CHARGER}" transform="scale(4 -4)">
                <path d="M 1,-1.6 C 1,-1.05 0,0 0,0 c 0,0 -1,-1.05 -1,-1.6 0,-0.55 0.45,-1 1,-1 0.55,0 1,0.45 1,1 z" style="fill: #ffe605"/>
                <circle style="fill: #ffffff" id="path4" r="0.7" cy="-1.6" cx="0"/>
            </g>
        """
    )
)


def _decompress_7z_base64_data(data: str) -> bytes:
    _LOGGER.debug("[decompress7zBase64Data] Begin")
    final_array = bytearray()

    # Decode Base64
    decoded = base64.b64decode(data)

    i = 0
    for idx in decoded:
        if i == 8:
            final_array += b"\x00\x00\x00\x00"
        final_array.append(idx)
        i += 1

    dec = lzma.LZMADecompressor(lzma.FORMAT_AUTO, None, None)
    decompressed_data = dec.decompress(final_array)

    _LOGGER.debug("[decompress7zBase64Data] Done")
    return decompressed_data


def _calc_value(value: float, min_value: float, max_value: float) -> float:
    try:
        if value is not None:
            # SVG allows sub-pixel precision, so we use floating point coordinates for better placement.
            new_value = (float(value) / _PIXEL_WIDTH) + _OFFSET
            # return value inside min and max
            return min(max_value, max(min_value, new_value))

    except (ZeroDivisionError, ValueError):
        pass

    return min_value or 0


def _calc_point(
    x: float, y: float, image_box: tuple[float, float, float, float] | None
) -> tuple[float, float]:
    if image_box is None:
        image_box = (0, 0, x, y)

    return (
        _calc_value(x, image_box[0], image_box[2]),
        _calc_value(y, image_box[1], image_box[3]),
    )


def _points_to_svg_path(
    points: Sequence[tuple[float, float]] | Sequence[tuple[float, float, bool, int]],
) -> list[svg.PathData]:
    # Convert a set of simple point (x, y), or trace points (x, y, connected, type) to a compacted
    # SVG path instruction.
    path_data: list[svg.PathData] = []

    # First instruction: move to the starting point using absolute coordinates
    first_p = points[0]
    path_data.append(svg.MoveTo(first_p[0], first_p[1]))

    for prev_p, p in itertools.pairwise(points):
        if p != prev_p:  # Skip repeated points
            if len(p) == 2 or p[2]:
                path_data.append(svg.LineToRel(p[0] - prev_p[0], p[1] - prev_p[1]))
            else:
                path_data.append(svg.MoveToRel(p[0] - prev_p[0], p[1] - prev_p[1]))

    # Further compact the path (keep only whitespaces between two numeric characters)
    return path_data


def _get_svg_positions(
    positions: list[Position],
    image_box: tuple[int, int, int, int] | None,
) -> list[svg.Element]:
    svg_positions: list[svg.Element] = []
    for position in sorted(positions, key=lambda x: _POSITIONS_SVG_ORDER[x.type]):
        pos = _calc_point(position.x, position.y, image_box)
        svg_positions.append(
            svg.Use(href=f"#position_{position.type}", x=pos[0], y=pos[1])
        )

    return svg_positions


def _get_svg_subset(
    subset: MapSubsetEvent,
    image_box: tuple[int, int, int, int] | None,
) -> svg.Path | svg.Polygon:
    subset_coordinates: list[int] = ast.literal_eval(subset.coordinates)

    points = [
        _calc_point(subset_coordinates[i], subset_coordinates[i + 1], image_box)
        for i in range(0, len(subset_coordinates), 2)
    ]

    if len(points) == 2:
        # Only 2 point, use a path
        return svg.Path(
            stroke=_COLORS[subset.type],
            stroke_width=1.5,
            stroke_dasharray=[4],
            vector_effect="non-scaling-stroke",
            d=_points_to_svg_path(points),
        )

    # For any other points count, return a polygon that should fit any required shape
    return svg.Polygon(
        fill=_COLORS[subset.type] + "90",  # Set alpha channel to 90 for fill color
        stroke=_COLORS[subset.type],
        stroke_width=1.5,
        stroke_dasharray=[4],
        vector_effect="non-scaling-stroke",
        points=list(sum(points, [])),  # Re-flatten the list of coordinates
    )


class Map:
    """Map representation."""

    def __init__(
        self,
        execute_command: Callable[[Command], Coroutine[Any, Any, None]],
        event_bus: EventBus,
    ) -> None:
        self._execute_command = execute_command
        self._event_bus = event_bus

        self._map_data: Final[MapData] = MapData(event_bus)
        self._amount_rooms: int = 0
        self._last_image: LastImage | None = None
        self._unsubscribers: list[Callable[[], None]] = []
        self._unsubscribers_internal: list[Callable[[], None]] = []
        self._tasks: set[asyncio.Future[Any]] = set()

        async def on_map_set(event: MapSetEvent) -> None:
            if event.type == MapSetType.ROOMS:
                self._amount_rooms = len(event.subsets)
                for room_id in self._map_data.rooms.copy():
                    if room_id not in event.subsets:
                        self._map_data.rooms.pop(room_id, None)
            else:
                for subset_id, subset in self._map_data.map_subsets.copy().items():
                    if subset.type == event.type and subset_id not in event.subsets:
                        self._map_data.map_subsets.pop(subset_id, None)

        self._unsubscribers_internal.append(
            self._event_bus.subscribe(MapSetEvent, on_map_set)
        )

        async def on_map_subset(event: MapSubsetEvent) -> None:
            if event.type == MapSetType.ROOMS and event.name:
                room = Room(event.name, event.id, event.coordinates)
                if self._map_data.rooms.get(event.id, None) != room:
                    self._map_data.rooms[room.id] = room

                    if len(self._map_data.rooms) == self._amount_rooms:
                        self._event_bus.notify(
                            RoomsEvent(list(self._map_data.rooms.values()))
                        )

            elif self._map_data.map_subsets.get(event.id, None) != event:
                self._map_data.map_subsets[event.id] = event

        self._unsubscribers_internal.append(
            self._event_bus.subscribe(MapSubsetEvent, on_map_subset)
        )

    # ---------------------------- METHODS ----------------------------

    def _update_trace_points(self, data: str) -> None:
        _LOGGER.debug("[_update_trace_points] Begin")
        trace_points = _decompress_7z_base64_data(data)

        for i in range(0, len(trace_points), 5):
            position_x: int = struct.unpack("<h", trace_points[i : i + 2])[0]
            position_y: int = struct.unpack("<h", trace_points[i + 2 : i + 4])[0]

            point_data = trace_points[i + 4]

            connected = point_data >> 7 & 1 == 0
            point_type = point_data & 1

            self._map_data.trace_values.append(
                (position_x, position_y, connected, point_type)
            )

        _LOGGER.debug("[_update_trace_points] finish")

    def _draw_map_pieces(self, draw: ImageDraw.ImageDraw) -> None:
        _LOGGER.debug("[_draw_map_pieces] Draw")
        image_x = 0
        image_y = 0

        for i in range(64):
            if i > 0:
                if i % 8 != 0:
                    image_y += 100
                else:
                    image_x += 100
                    image_y = 0

            current_piece = self._map_data.map_pieces[i]
            if current_piece.in_use:
                for x in range(100):
                    current_column = current_piece.points[x]
                    for y in range(100):
                        pixel_type = current_column[y]
                        point_x = image_x + x
                        point_y = image_y + y
                        if (point_x > 6400) or (point_y > 6400):
                            _LOGGER.error(
                                "[get_base64_map] Map Limit 6400!! X: %d Y: %d",
                                point_x,
                                point_y,
                            )
                            raise MapError("Map Limit reached!")
                        if pixel_type in [0x01, 0x02, 0x03]:
                            draw.point((point_x, point_y), fill=_COLORS[pixel_type])

    def _get_svg_traces_path(self) -> svg.Path | None:
        if len(self._map_data.trace_values) > 0:
            _LOGGER.debug("[get_svg_map] Draw Trace")

            return svg.Path(
                fill="none",
                stroke=_COLORS[_TRACE_MAP],
                stroke_width=1.5,
                stroke_linejoin="round",
                vector_effect="non-scaling-stroke",
                transform=[svg.Translate(_OFFSET, _OFFSET), svg.Scale(0.2, 0.2)],
                d=_points_to_svg_path(self._map_data.trace_values),
            )

        return None

    def _get_svg_rooms(
        self,
        image_box: tuple[int, int, int, int],
        image_box_center: tuple[float, float],
    ) -> tuple[list[svg.Element], list[svg.Element]]:
        svg_rooms_elements: list[svg.Element] = []
        svg_rooms_labels: list[svg.Element] = []

        for room, color in zip(
            sorted(self._map_data.rooms.keys()), itertools.cycle(_ROOM_COLORS)
        ):
            # Split coordinates into a flat sequence
            room_coords = re.split(
                "[;,]",
                _decompress_7z_base64_data(
                    self._map_data.rooms[room].coordinates
                ).decode("ascii"),
            )

            # Append to room svg elements
            svg_rooms_elements.append(
                svg.Polygon(
                    id=f"room_{room}",
                    fill=color + "50",
                    stroke=color + "A0",
                    stroke_width=2,
                    vector_effect="non-scaling-stroke",
                    transform=[svg.Translate(_OFFSET, _OFFSET), svg.Scale(0.02, 0.02)],
                    points=list(map(int, room_coords)),
                )
            )

            room_name = self._map_data.rooms[room].name
            if room_name != "Default":
                # Calculate label positions (cannot use SVG transformations to vertically flip coordinates, as transformations are
                # applied to the whole text, which would result in text to be vertically flipped...)

                # Get a rough room center.
                room_center_x = sum(float(x) for x in room_coords[0::2]) / (
                    len(room_coords) / 2
                )
                room_center_y = sum(float(y) for y in room_coords[1::2]) / (
                    len(room_coords) / 2
                )

                # Get map relative position
                room_center_p = _calc_point(room_center_x, room_center_y, image_box)

                # Add the text, with position vertically flipped on map center
                svg_rooms_labels.append(
                    svg.Text(
                        id=f"room_label_{room}",
                        x=room_center_p[0],
                        y=image_box_center[1] - room_center_p[1] + image_box_center[1],
                        dominant_baseline="middle",
                        text_anchor="middle",
                        font_family="sans-serif",
                        font_size=svg.Length(4, "pt"),
                        style="user_select: none",
                        text=room_name,
                    )
                )

        return (svg_rooms_elements, svg_rooms_labels)

    def enable(self) -> None:
        """Enable map."""
        if self._unsubscribers:
            return

        create_task(self._tasks, self._execute_command(GetCachedMapInfo()))

        async def on_position(event: PositionsEvent) -> None:
            self._map_data.positions = event.positions

        self._unsubscribers.append(
            self._event_bus.subscribe(PositionsEvent, on_position)
        )

        async def on_map_trace(event: MapTraceEvent) -> None:
            if event.start == 0:
                self._map_data.trace_values.clear()

            self._update_trace_points(event.data)

        self._unsubscribers.append(
            self._event_bus.subscribe(MapTraceEvent, on_map_trace)
        )

        async def on_major_map(event: MajorMapEvent) -> None:
            async with asyncio.TaskGroup() as tg:
                for idx, value in enumerate(event.values):
                    if (
                        self._map_data.map_pieces[idx].crc32_indicates_update(value)
                        and event.requested
                    ):
                        tg.create_task(
                            self._execute_command(
                                GetMinorMap(map_id=event.map_id, piece_index=idx)
                            )
                        )

        self._unsubscribers.append(
            self._event_bus.subscribe(MajorMapEvent, on_major_map)
        )

        async def on_minor_map(event: MinorMapEvent) -> None:
            self._map_data.map_pieces[event.index].update_points(event.value)

        self._unsubscribers.append(
            self._event_bus.subscribe(MinorMapEvent, on_minor_map)
        )

    def disable(self) -> None:
        """Disable map."""
        self._unsubscribe_from(self._unsubscribers)

    def _unsubscribe_from(self, unsubscribers: list[Callable[[], None]]) -> None:
        for unsubscribe in unsubscribers:
            unsubscribe()
        unsubscribers.clear()

    def refresh(self) -> None:
        """Manually refresh map."""
        if not self._unsubscribers:
            raise MapError("Please enable the map first")

        # TODO make it nice pylint: disable=fixme
        self._event_bus.request_refresh(PositionsEvent)
        self._event_bus.request_refresh(MapTraceEvent)
        self._event_bus.request_refresh(MajorMapEvent)

    def get_svg_map(self, width: int | None = None) -> str:
        """Return map as SVG string."""
        if not self._unsubscribers:
            raise MapError("Please enable the map first")

        if (
            self._last_image is not None
            and width == self._last_image.width
            and not self._map_data.changed
        ):
            _LOGGER.debug("[get_svg_map] No need to update")
            return self._last_image.svg_image

        _LOGGER.debug("[get_svg_map] Begin")

        image = Image.new("RGBA", (6400, 6400))
        draw = ImageDraw.ImageDraw(image)
        self._draw_map_pieces(draw)
        del draw

        image_box = image.getbbox()

        if image_box:
            image_box_center = (
                (image_box[0] + image_box[2]) / 2,
                (image_box[1] + image_box[3]) / 2,
            )

            _LOGGER.debug("[get_svg_map] Crop Image")
            cropped = image.crop(image_box)
            del image

            _LOGGER.debug(
                "[get_svg_map] Map current Size: X: %d Y: %d",
                cropped.size[0],
                cropped.size[1],
            )

            _LOGGER.debug("[get_svg_map] Saving to buffer")
            buffered = BytesIO()
            cropped.save(buffered, format="PNG")
            del cropped

            base64_bg = base64.b64encode(buffered.getvalue())

            # Build the SVG XML

            svg_positions = _get_svg_positions(self._map_data.positions, image_box)

            svg_subset_elements: list[svg.Element] = [
                _get_svg_subset(subset, image_box)
                for subset in self._map_data.map_subsets.values()
            ]

            svg_rooms_elements, svg_rooms_labels = self._get_svg_rooms(
                image_box, image_box_center
            )

            svg_traces_path = self._get_svg_traces_path()

            # Elements of the SVG Map
            svg_map_group_elements: list[svg.Element] = []

            # Map background.
            svg_map_group_elements.append(
                svg.Image(
                    x=image_box[0],
                    y=image_box[1],
                    width=image_box[2] - image_box[0],
                    height=image_box[3] - image_box[1],
                    style="image-rendering: pixelated",
                    href=f"data:image/png;base64,{base64_bg.decode('ascii')}",
                )
            )

            # Rooms
            svg_map_group_elements.extend(svg_rooms_elements)

            # Additional subsets (VirtualWalls and NoMopZones)
            svg_map_group_elements.extend(svg_subset_elements)

            # Traces (if any)
            if svg_traces_path:
                svg_map_group_elements.append(svg_traces_path)

            # Bot and Charge stations
            svg_map_group_elements.extend(svg_positions)

            # Build the complete SVG map
            svg_map = svg.SVG(
                viewBox=svg.ViewBoxSpec(
                    image_box[0] - _SVG_MAP_MARGIN,
                    image_box[1] - _SVG_MAP_MARGIN,
                    (image_box[2] - image_box[0]) + _SVG_MAP_MARGIN * 2,
                    image_box[3] - image_box[1] + _SVG_MAP_MARGIN * 2,
                ),
                elements=[
                    _SVG_DEFS,
                    svg.G(
                        id="map_group",
                        transform_origin=f"{image_box_center[0]} {image_box_center[1]}",
                        transform=[svg.Scale(1, -1)],
                        elements=svg_map_group_elements,
                    ),
                    svg.G(elements=svg_rooms_labels),
                ],
            )

        else:
            # No map data yet, generate an empty SVG.
            svg_map = svg.SVG()

        str_svg_map = str(svg_map)
        self._map_data.reset_changed()
        self._last_image = LastImage(str_svg_map, width)
        _LOGGER.debug("[get_svg_map] Finish")

        return str_svg_map

    async def teardown(self) -> None:
        """Teardown map."""
        self.disable()
        self._unsubscribe_from(self._unsubscribers_internal)
        await cancel(self._tasks)


class MapPiece:
    """Map piece representation."""

    _NOT_INUSE_CRC32: int = 1295764014

    def __init__(self, on_change: Callable[[], None], index: int) -> None:
        self._on_change = on_change
        self._index = index
        self._points: NDArray[float64] | None = None
        self._crc32: int = MapPiece._NOT_INUSE_CRC32

    def crc32_indicates_update(self, crc32: str) -> bool:
        """Return True if update is required."""
        crc32_int = int(crc32)
        if crc32_int == MapPiece._NOT_INUSE_CRC32:
            self._crc32 = crc32_int
            self._points = None
            return False

        return self._crc32 != crc32_int

    @property
    def in_use(self) -> bool:
        """Return True if piece is in use."""
        return self._crc32 != MapPiece._NOT_INUSE_CRC32

    @property
    def points(self) -> NDArray[float64]:
        """I'm the 'x' property."""
        if not self.in_use or self._points is None:
            return zeros((100, 100))
        return self._points

    def update_points(self, base64_data: str) -> None:
        """Add map piece points."""
        decoded = _decompress_7z_base64_data(base64_data)
        old_crc32 = self._crc32
        self._crc32 = zlib.crc32(decoded)

        if self._crc32 != old_crc32:
            self._on_change()

        if self.in_use:
            self._points = reshape(list(decoded), (100, 100))
        else:
            self._points = None

    def __hash__(self) -> int:
        """Calculate hash on index and crc32."""
        return hash(self._index) + hash(self._crc32)

    def __eq__(self, obj: object) -> bool:
        if not isinstance(obj, MapPiece):
            return False

        return self._crc32 == obj._crc32 and self._index == obj._index


@dataclasses.dataclass(frozen=True)
class LastImage:
    """Last created image."""

    svg_image: str
    width: int | None


class MapData:
    """Map data."""

    def __init__(self, event_bus: EventBus) -> None:
        self._changed: bool = False

        def on_change() -> None:
            self._changed = True
            event_bus.notify(MapChangedEvent(datetime.now(UTC)), debounce_time=1)

        self._on_change = on_change
        self._map_pieces: OnChangedList[MapPiece] = OnChangedList(
            on_change, [MapPiece(on_change, i) for i in range(64)]
        )
        self._map_subsets: OnChangedDict[int, MapSubsetEvent] = OnChangedDict(on_change)
        self._positions: OnChangedList[Position] = OnChangedList(on_change)
        self._rooms: OnChangedDict[int, Room] = OnChangedDict(on_change)
        self._trace_values: OnChangedList[tuple[int, int, bool, int]] = OnChangedList(
            on_change
        )

    @property
    def changed(self) -> bool:
        """Indicate if data was changed."""
        return self._changed

    @property
    def map_pieces(self) -> OnChangedList[MapPiece]:
        """Return map pieces."""
        return self._map_pieces

    @property
    def map_subsets(self) -> dict[int, MapSubsetEvent]:
        """Return map subsets."""
        return self._map_subsets

    @property
    def positions(self) -> list[Position]:
        """Return positions."""
        return self._positions

    @positions.setter
    def positions(self, value: list[Position]) -> None:
        if not isinstance(value, OnChangedList):
            value = OnChangedList(self._on_change, value)
        self._positions = value
        self._changed = True

    @property
    def rooms(self) -> dict[int, Room]:
        """Return rooms."""
        return self._rooms

    @property
    def trace_values(self) -> OnChangedList[tuple[int, int, bool, int]]:
        """Return trace values."""
        return self._trace_values

    def reset_changed(self) -> None:
        """Reset changed value."""
        self._changed = False
