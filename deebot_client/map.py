"""Map module."""
import ast
import asyncio
import base64
from collections.abc import Callable, Coroutine, Sequence
import dataclasses
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
import itertools
import lzma
import struct
from typing import Any, Final
import zlib

from PIL import Image, ImageColor, ImageOps, ImagePalette
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


def _attributes_as_str(self) -> str:  # type: ignore[no-untyped-def] # noqa: ANN001
    """Return attributes as compact svg string."""
    result = ""
    for p in dataclasses.astuple(self):
        value = p
        if isinstance(p, bool):
            value = int(p)
        if result == "" or (isinstance(value, Decimal | float | int) and value < 0):
            result += f"{value}"
        else:
            # only positive values need to have a space
            result += f" {value}"
    return result


svg.PathData.attributes_as_str = _attributes_as_str  # type: ignore[attr-defined]

_ALWAYS_WRITE_COMMAND_NAME: tuple[str, ...] = (
    svg.MoveTo.command,
    svg.MoveToRel.command,
)


@dataclasses.dataclass
class Path(svg.Path):  # noqa: TID251
    """Path which removes unnecessary spaces."""

    @classmethod
    def _as_str(cls, val: Any) -> str:
        if isinstance(val, list) and val and isinstance(val[0], svg.PathData):
            result = ""
            current = None
            for elem in val:
                if hasattr(elem, "attributes_as_str"):
                    attributes = elem.attributes_as_str()
                    # if the command is the same as the previous one, we can omit it
                    if (
                        current != elem.command
                        or elem.command in _ALWAYS_WRITE_COMMAND_NAME
                    ):
                        current = elem.command
                        result += elem.command
                    elif attributes[0] != "-":
                        # only positive values need to have a space
                        result += " "
                    result += elem.attributes_as_str()
                else:
                    current = None
                    result += cls._as_str(elem)
            return result
        return super()._as_str(val)


_LOGGER = get_logger(__name__)
_PIXEL_WIDTH = 50
_ROUND_TO_DIGITS = 3


@dataclasses.dataclass(frozen=True)
class _PositionSvg:
    order: int
    svg_id: str


_POSITIONS_SVG = {
    PositionType.DEEBOT: _PositionSvg(0, "d"),
    PositionType.CHARGER: _PositionSvg(1, "c"),
}

_OFFSET = 400
_TRACE_MAP = "trace_map"
_COLORS = {
    _TRACE_MAP: "#fff",
    MapSetType.VIRTUAL_WALLS: "#f00",
    MapSetType.NO_MOP_ZONES: "#ffa500",
}
_DEFAULT_MAP_BACKGROUND_COLOR = ImageColor.getrgb("#badaff")  # floor
_MAP_BACKGROUND_COLORS: dict[int, tuple[int, ...]] = {
    0: ImageColor.getrgb("#000000"),  # unknown (will be transparent)
    1: _DEFAULT_MAP_BACKGROUND_COLOR,  # floor
    2: ImageColor.getrgb("#4e96e2"),  # wall
    3: ImageColor.getrgb("#1a81ed"),  # carpet
    4: ImageColor.getrgb("#dee9fb"),  # not scanned space
    5: ImageColor.getrgb("#edf3fb"),  # possible obstacle
    # fallsback to _DEFAULT_MAP_BACKGROUND_COLOR for any other value
}


@dataclasses.dataclass(frozen=True)
class Point:
    """Point."""

    x: float
    y: float

    def flatten(self) -> tuple[float, float]:
        """Flatten point."""
        return (self.x, self.y)


@dataclasses.dataclass(frozen=True)
class TracePoint(Point):
    """Trace point."""

    connected: bool


@dataclasses.dataclass
class AxisManipulation:
    """Map manipulation."""

    map_shift: float
    svg_max: float
    _transform: Callable[[float, float], float] | None = None

    def __post_init__(self) -> None:
        self._svg_center = self.svg_max / 2

    def transform(self, value: float) -> float:
        """Transform value."""
        if self._transform is None:
            return value
        return self._transform(self._svg_center, value)


@dataclasses.dataclass
class MapManipulation:
    """Map manipulation."""

    x: AxisManipulation
    y: AxisManipulation


@dataclasses.dataclass
class BackgroundImage:
    """Background image."""

    bounding_box: tuple[float, float, float, float]
    image: bytes


# SVG definitions referred by map elements
_SVG_DEFS = svg.Defs(
    elements=[
        # Gradient used by Bot icon
        svg.RadialGradient(
            id=f"{_POSITIONS_SVG[PositionType.DEEBOT].svg_id}bg",
            cx=svg.Length(50, "%"),
            cy=svg.Length(50, "%"),
            r=svg.Length(50, "%"),
            fx=svg.Length(50, "%"),
            fy=svg.Length(50, "%"),
            elements=[
                svg.Stop(offset=svg.Length(70, "%"), style="stop-color:#00f"),
                svg.Stop(offset=svg.Length(97, "%"), style="stop-color:#00f0"),
            ],
        ),
        # Bot circular icon
        svg.G(
            id=_POSITIONS_SVG[PositionType.DEEBOT].svg_id,
            elements=[
                svg.Circle(
                    r=5, fill=f"url(#{_POSITIONS_SVG[PositionType.DEEBOT].svg_id}bg)"
                ),
                svg.Circle(r=3.5, stroke="white", fill="blue", stroke_width=0.5),
            ],
        ),
        # Charger pin icon (pre-flipped vertically)
        svg.G(
            id=_POSITIONS_SVG[PositionType.CHARGER].svg_id,
            elements=[
                Path(
                    fill="#ffe605",
                    d=[
                        svg.M(4, -6.4),
                        svg.C(4, -4.2, 0, 0, 0, 0),
                        svg.s(-4, -4.2, -4, -6.4),
                        svg.s(1.8, -4, 4, -4),
                        svg.s(4, 1.8, 4, 4),
                        svg.Z(),
                    ],
                ),
                svg.Circle(fill="#fff", r=2.8, cy=-6.4),
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


def _calc_value(value: float, axis_manipulation: AxisManipulation) -> float:
    try:
        if value is not None:
            # SVG allows sub-pixel precision, so we use floating point coordinates for better placement.
            new_value = (
                (float(value) / _PIXEL_WIDTH) + _OFFSET - axis_manipulation.map_shift
            )
            new_value = axis_manipulation.transform(new_value)
            # return value inside min and max
            return round(
                min(axis_manipulation.svg_max, max(0, new_value)), _ROUND_TO_DIGITS
            )

    except (ZeroDivisionError, ValueError):
        pass

    return 0


def _calc_point(
    x: float,
    y: float,
    map_manipulation: MapManipulation,
) -> Point:
    return Point(
        _calc_value(x, map_manipulation.x),
        _calc_value(y, map_manipulation.y),
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
        x = round(p.x - prev_p.x, _ROUND_TO_DIGITS)
        y = round(p.y - prev_p.y, _ROUND_TO_DIGITS)
        if x == 0 and y == 0:
            continue
        if isinstance(p, TracePoint) and not p.connected:
            path_data.append(svg.MoveToRel(x, y))
        elif x == 0:
            path_data.append(svg.VerticalLineToRel(y))
        elif y == 0:
            path_data.append(svg.HorizontalLineToRel(x))
        else:
            path_data.append(svg.LineToRel(x, y))
    return path_data


def _get_svg_positions(
    positions: list[Position],
    map_manipulation: MapManipulation,
) -> list[svg.Element]:
    svg_positions: list[svg.Element] = []
    for position in sorted(positions, key=lambda x: _POSITIONS_SVG[x.type].order):
        pos = _calc_point(position.x, position.y, map_manipulation)
        svg_positions.append(
            svg.Use(href=f"#{_POSITIONS_SVG[position.type].svg_id}", x=pos.x, y=pos.y)
        )

    return svg_positions


def _get_svg_subset(
    subset: MapSubsetEvent,
    map_manipulation: MapManipulation,
) -> Path | svg.Polygon:
    subset_coordinates: list[int] = ast.literal_eval(subset.coordinates)

    points = [
        _calc_point(
            subset_coordinates[i],
            subset_coordinates[i + 1],
            map_manipulation,
        )
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
        points=[num for p in points for num in p.flatten()],
    )


def _set_image_palette(image: Image.Image) -> Image.Image:
    """Dynamically create color palette for map image."""
    palette_colors: list[int] = []
    for idx in range(256):
        palette_colors.extend(
            _MAP_BACKGROUND_COLORS.get(idx, _DEFAULT_MAP_BACKGROUND_COLOR)
        )
    source_palette = ImagePalette.ImagePalette("RGB", palette_colors)

    image.info["transparency"] = 0

    return image.remap_palette(
        [c[1] for c in image.getcolors()], source_palette.tobytes()
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
        self._last_image: str | None = None
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

            self._map_data.trace_values.append(
                TracePoint(position_x, position_y, connected)
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

    def _get_svg_traces_path(
        self,
        map_manipulation: MapManipulation,
    ) -> Path | None:
        if len(self._map_data.trace_values) > 0:
            _LOGGER.debug("[get_svg_map] Draw Trace")
            return Path(
                fill="none",
                stroke=_COLORS[_TRACE_MAP],
                stroke_width=1.5,
                stroke_linejoin="round",
                vector_effect="non-scaling-stroke",
                transform=[
                    svg.Translate(
                        _OFFSET - map_manipulation.x.map_shift,
                        _OFFSET - map_manipulation.y.map_shift,
                    ),
                    svg.Scale(0.2, 0.2),
                ],
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

    def _get_background_image(self) -> BackgroundImage | None:
        """Return background image."""
        image = Image.new("P", (6400, 6400))
        self._draw_map_pieces(image)

        bounding_box = image.getbbox()
        if bounding_box is None:
            return None

        image = ImageOps.flip(image.crop(bounding_box))
        image = _set_image_palette(image)

        buffered = BytesIO()
        image.save(buffered, format="PNG", optimize=True)

        return BackgroundImage(
            bounding_box,
            buffered.getvalue(),
        )

    def get_svg_map(self) -> str:
        """Return map as SVG string."""
        if not self._unsubscribers:
            raise MapError("Please enable the map first")

        if self._last_image and not self._map_data.changed:
            _LOGGER.debug("[get_svg_map] No need to update")
            return self._last_image

        _LOGGER.debug("[get_svg_map] Begin")

        # Reset change before starting to build the SVG
        self._map_data.reset_changed()

        svg_map = svg.SVG()
        if background := self._get_background_image():
            # Build the SVG elements
            svg_map.elements = [_SVG_DEFS]
            manipulation = MapManipulation(
                AxisManipulation(
                    map_shift=background.bounding_box[0],
                    svg_max=background.bounding_box[2] - background.bounding_box[0],
                ),
                AxisManipulation(
                    map_shift=background.bounding_box[1],
                    svg_max=background.bounding_box[3] - background.bounding_box[1],
                    _transform=lambda c, v: 2 * c - v,
                ),
            )

            # Set map viewBox based on background map bounding box.
            svg_map.viewBox = svg.ViewBoxSpec(
                0,
                0,
                manipulation.x.svg_max,
                manipulation.y.svg_max,
            )

            # Map background.
            svg_map.elements.append(
                svg.Image(
                    style="image-rendering: pixelated",
                    href=f"data:image/png;base64,{base64.b64encode(background.image).decode('ascii')}",
                )
            )

            # Additional subsets (VirtualWalls and NoMopZones)
            svg_map.elements.extend(
                [
                    _get_svg_subset(subset, manipulation)
                    for subset in self._map_data.map_subsets.values()
                ]
            )

            # Traces (if any)
            if svg_traces_path := self._get_svg_traces_path(manipulation):
                svg_map.elements.append(
                    # Elements to vertically flip
                    svg.G(
                        transform_origin=r"50% 50%",
                        transform=[svg.Scale(1, -1)],
                        elements=[svg_traces_path],
                    )
                )

            # Bot and Charge stations
            svg_map.elements.extend(
                _get_svg_positions(self._map_data.positions, manipulation)
            )

        str_svg_map = str(svg_map)

        self._last_image = str_svg_map

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
