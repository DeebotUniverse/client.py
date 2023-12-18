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
import struct
from typing import Any, Final, NamedTuple
import zlib

from PIL import Image, ImageColor, ImagePalette
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


def _path_data_str(self) -> str:  # type: ignore[no-untyped-def] # noqa: ANN001
    points = []
    for p in dataclasses.astuple(self):
        value = p
        if isinstance(p, bool):
            value = int(p)
        points.append(str(value))
    joined = " ".join(points)
    return f"{self.command}{joined}"


svg.PathData.__str__ = _path_data_str  # type: ignore[method-assign]


@dataclasses.dataclass
class Path(svg.Path):
    """Path which removes unnecessary spaces."""

    @classmethod
    def _as_str(cls, val: Any) -> str:
        if isinstance(val, list) and val and isinstance(val[0], svg.PathData):
            return "".join(cls._as_str(v) for v in val)
        return super()._as_str(val)


_LOGGER = get_logger(__name__)
_PIXEL_WIDTH = 50

_POSITIONS_SVG_ORDER = {
    PositionType.DEEBOT: 0,
    PositionType.CHARGER: 1,
}

_SVG_MAP_MARGIN = 5

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
_MAP_BACKGROUND_COLORS = [
    "#000000",  # 0 -> unknown (will be transparent)
    "#badaff",  # 1 -> floor
    "#4e96e2",  # 2 -> wall
    "#1a81ed",  # 3 -> carpet
]
_MAP_BACKGROUND_IMAGE_PALETTE = ImagePalette.ImagePalette(
    "RGB",
    [value for color in _MAP_BACKGROUND_COLORS for value in ImageColor.getrgb(color)],
)


class Point(NamedTuple):
    """Point."""

    x: float
    y: float


class TracePoint(NamedTuple):
    """Trace point."""

    x: int
    y: int
    connected: bool
    type: int


# SVG definitions referred by map elements
_SVG_DEFS = svg.Defs(
    elements=[
        # Gradient used by Bot icon
        svg.RadialGradient(
            id="device_bg",
            cx=svg.Length(50, "%"),
            cy=svg.Length(50, "%"),
            r=svg.Length(50, "%"),
            fx=svg.Length(50, "%"),
            fy=svg.Length(50, "%"),
            elements=[
                svg.Stop(offset=svg.Length(70, "%"), style="stop-color:#0000FF;"),
                svg.Stop(offset=svg.Length(97, "%"), style="stop-color:#0000FF00;"),
            ],
        ),
        # Bot circular icon
        svg.G(
            id=f"position_{PositionType.DEEBOT}",
            elements=[
                svg.Circle(r=5, fill="url(#device_bg)"),
                svg.Circle(r=3.5, stroke="white", fill="blue", stroke_width=0.5),
            ],
        ),
        # Charger pin icon (pre-flipped vertically)
        svg.G(
            id=f"position_{PositionType.CHARGER}",
            transform=[svg.Scale(4, -4)],
            elements=[
                Path(
                    fill="#ffe605",
                    d=[
                        svg.M(1, -1.6),
                        svg.C(1, -1.05, 0, 0, 0, 0),
                        svg.c(0, 0, -1, -1.05, -1, -1.6),
                        svg.c(0, -0.55, 0.45, -1, 1, -1),
                        svg.c(0.55, 0, 1, 0.45, 1, 1),
                        svg.Z(),
                    ],
                ),
                svg.Circle(fill="white", r=0.7, cy=-1.6, cx=0),
            ],
        ),
    ]
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
) -> Point:
    if image_box is None:
        image_box = (0, 0, x, y)

    return Point(
        _calc_value(x, image_box[0], image_box[2]),
        _calc_value(y, image_box[1], image_box[3]),
    )


def _points_to_svg_path(
    points: Sequence[Point | TracePoint],
) -> list[svg.PathData]:
    # Convert a set of simple point (x, y), or trace points (x, y, connected, type) to
    # SVG path instructions.
    path_data: list[svg.PathData] = []

    # First instruction: move to the starting point using absolute coordinates
    first_p = points[0]
    path_data.append(svg.MoveTo(first_p.x, first_p.y))

    for prev_p, p in itertools.pairwise(points):
        x = p.x - prev_p.x
        y = p.y - prev_p.y
        if isinstance(p, TracePoint) and not p.connected:
            path_data.append(svg.MoveToRel(x, y))
        elif x == 0:
            if y == 0:
                continue
            path_data.append(svg.VerticalLineToRel(y))
        elif y == 0:
            path_data.append(svg.HorizontalLineToRel(x))
        else:
            path_data.append(svg.LineToRel(x, y))
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
        return Path(
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
            position_x, position_y = struct.unpack("<hh", trace_points[i : i + 4])

            point_data = trace_points[i + 4]

            connected = point_data >> 7 & 1 == 0
            point_type = point_data & 1

            self._map_data.trace_values.append(
                TracePoint(position_x, position_y, connected, point_type)
            )

        _LOGGER.debug("[_update_trace_points] finish")

    def _draw_map_pieces(self, image: Image.Image) -> None:
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
                image.paste(current_piece.image, (image_x, image_y))

    def _get_svg_traces_path(self) -> svg.Path | None:
        if len(self._map_data.trace_values) > 0:
            _LOGGER.debug("[get_svg_map] Draw Trace")

            return Path(
                fill="none",
                stroke=_COLORS[_TRACE_MAP],
                stroke_width=1.5,
                stroke_linejoin="round",
                vector_effect="non-scaling-stroke",
                transform=[svg.Translate(_OFFSET, _OFFSET), svg.Scale(0.2, 0.2)],
                d=_points_to_svg_path(self._map_data.trace_values),
            )

        return None

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

        image = Image.new("P", (6400, 6400))
        image.putpalette(_MAP_BACKGROUND_IMAGE_PALETTE)
        image.info["transparency"] = 0
        self._draw_map_pieces(image)

        svg_map = svg.SVG()
        if image_box := image.getbbox():
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

            # Build the SVG elements

            svg_positions = _get_svg_positions(self._map_data.positions, image_box)

            svg_subset_elements: list[svg.Element] = [
                _get_svg_subset(subset, image_box)
                for subset in self._map_data.map_subsets.values()
            ]

            svg_traces_path = self._get_svg_traces_path()

            # Elements of the SVG Map to vertically flip
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

            # Additional subsets (VirtualWalls and NoMopZones)
            svg_map_group_elements.extend(svg_subset_elements)

            # Traces (if any)
            if svg_traces_path:
                svg_map_group_elements.append(svg_traces_path)

            # Bot and Charge stations
            svg_map_group_elements.extend(svg_positions)

            # Set map viewBox based on background map bounding box.
            svg_map.viewBox = svg.ViewBoxSpec(
                image_box[0] - _SVG_MAP_MARGIN,
                image_box[1] - _SVG_MAP_MARGIN,
                (image_box[2] - image_box[0]) + _SVG_MAP_MARGIN * 2,
                image_box[3] - image_box[1] + _SVG_MAP_MARGIN * 2,
            )

            # Add all elements to the SVG map
            svg_map.elements = [
                _SVG_DEFS,
                # Elements to vertically flip
                svg.G(
                    transform_origin=f"{image_box_center[0]} {image_box_center[1]}",
                    transform=[svg.Scale(1, -1)],
                    elements=svg_map_group_elements,
                ),
            ]

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
        self._crc32: int = MapPiece._NOT_INUSE_CRC32
        self._image: Image.Image | None = None

    def crc32_indicates_update(self, crc32: str) -> bool:
        """Return True if update is required."""
        crc32_int = int(crc32)
        if crc32_int == MapPiece._NOT_INUSE_CRC32:
            self._crc32 = crc32_int
            self._image = None
            return False

        return self._crc32 != crc32_int

    @property
    def in_use(self) -> bool:
        """Return True if piece is in use."""
        return self._crc32 != MapPiece._NOT_INUSE_CRC32

    @property
    def image(self) -> Image.Image:
        """I'm the 'x' property."""
        if not self.in_use or self._image is None:
            return Image.new("P", (100, 100))
        return self._image

    def update_points(self, base64_data: str) -> None:
        """Add map piece points."""
        decoded = _decompress_7z_base64_data(base64_data)
        old_crc32 = self._crc32
        self._crc32 = zlib.crc32(decoded)

        if self._crc32 != old_crc32:
            self._on_change()

        if self.in_use:
            im = Image.frombytes("P", (100, 100), decoded, "raw", "P", 0, -1)
            im.putpalette(_MAP_BACKGROUND_IMAGE_PALETTE)
            im.info["transparency"] = 0
            self._image = im.rotate(-90)
        else:
            self._image = None

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
        self._trace_values: OnChangedList[TracePoint] = OnChangedList(on_change)

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
    def trace_values(self) -> OnChangedList[TracePoint]:
        """Return trace values."""
        return self._trace_values

    def reset_changed(self) -> None:
        """Reset changed value."""
        self._changed = False
