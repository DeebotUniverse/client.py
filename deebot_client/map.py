"""Map module."""
import ast
import asyncio
import base64
import dataclasses
import lzma
import math
import struct
import zlib
from collections.abc import Callable, Coroutine
from io import BytesIO
from typing import Any, Final

from numpy import ndarray, reshape, zeros
from PIL import Image, ImageDraw, ImageOps

from .command import Command
from .commands import GetCachedMapInfo, GetMinorMap
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
from .events.event_bus import EventBus, EventListener
from .exceptions import MapError
from .logging_filter import get_logger
from .models import Room
from .util import OnChangedDict, OnChangedList

_LOGGER = get_logger(__name__)
_PIXEL_WIDTH = 50
_POSITION_PNG = {
    PositionType.DEEBOT: "iVBORw0KGgoAAAANSUhEUgAAAAYAAAAGCAIAAABvrngfAAAACXBIWXMAAAsTAAALEwEAmpwYAAAF0WlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgNS42LWMxNDUgNzkuMTYzNDk5LCAyMDE4LzA4LzEzLTE2OjQwOjIyICAgICAgICAiPiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtbG5zOnhtcE1NPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvbW0vIiB4bWxuczpzdEV2dD0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL3NUeXBlL1Jlc291cmNlRXZlbnQjIiB4bWxuczpkYz0iaHR0cDovL3B1cmwub3JnL2RjL2VsZW1lbnRzLzEuMS8iIHhtbG5zOnBob3Rvc2hvcD0iaHR0cDovL25zLmFkb2JlLmNvbS9waG90b3Nob3AvMS4wLyIgeG1wOkNyZWF0b3JUb29sPSJBZG9iZSBQaG90b3Nob3AgQ0MgMjAxOSAoV2luZG93cykiIHhtcDpDcmVhdGVEYXRlPSIyMDIwLTA1LTI0VDEyOjAzOjE2KzAyOjAwIiB4bXA6TWV0YWRhdGFEYXRlPSIyMDIwLTA1LTI0VDEyOjAzOjE2KzAyOjAwIiB4bXA6TW9kaWZ5RGF0ZT0iMjAyMC0wNS0yNFQxMjowMzoxNiswMjowMCIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDo0YWM4NWY5MC1hNWMwLTE2NDktYTQ0MC0xMWM0NWY5OGQ1MDYiIHhtcE1NOkRvY3VtZW50SUQ9ImFkb2JlOmRvY2lkOnBob3Rvc2hvcDo3Zjk3MTZjMi1kZDM1LWJiNDItYjMzZS1hYjYwY2Y4ZTZlZDYiIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDpiMzhiNGZlMS1lOGNkLTJjNDctYmQwZC1lNmZiNzRhMjFkMDciIGRjOmZvcm1hdD0iaW1hZ2UvcG5nIiBwaG90b3Nob3A6Q29sb3JNb2RlPSIzIj4gPHhtcE1NOkhpc3Rvcnk+IDxyZGY6U2VxPiA8cmRmOmxpIHN0RXZ0OmFjdGlvbj0iY3JlYXRlZCIgc3RFdnQ6aW5zdGFuY2VJRD0ieG1wLmlpZDpiMzhiNGZlMS1lOGNkLTJjNDctYmQwZC1lNmZiNzRhMjFkMDciIHN0RXZ0OndoZW49IjIwMjAtMDUtMjRUMTI6MDM6MTYrMDI6MDAiIHN0RXZ0OnNvZnR3YXJlQWdlbnQ9IkFkb2JlIFBob3Rvc2hvcCBDQyAyMDE5IChXaW5kb3dzKSIvPiA8cmRmOmxpIHN0RXZ0OmFjdGlvbj0ic2F2ZWQiIHN0RXZ0Omluc3RhbmNlSUQ9InhtcC5paWQ6NGFjODVmOTAtYTVjMC0xNjQ5LWE0NDAtMTFjNDVmOThkNTA2IiBzdEV2dDp3aGVuPSIyMDIwLTA1LTI0VDEyOjAzOjE2KzAyOjAwIiBzdEV2dDpzb2Z0d2FyZUFnZW50PSJBZG9iZSBQaG90b3Nob3AgQ0MgMjAxOSAoV2luZG93cykiIHN0RXZ0OmNoYW5nZWQ9Ii8iLz4gPC9yZGY6U2VxPiA8L3htcE1NOkhpc3Rvcnk+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+AP7+NwAAAFpJREFUCJllzEEKgzAQhtFvMkSsEKj30oUXrYserELA1obhd+nCd4BnksZ53X4Cnr193ov59Iq+o2SA2vz4p/iKkgkRouTYlbhJ/jBqww03avPBTNI4rdtx9ScfWyYCg52e0gAAAABJRU5ErkJggg==",  # nopep8
    PositionType.CHARGER: "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAOCAYAAAAWo42rAAAAdUlEQVQoU2NkQAP/nzD8BwkxyjAwIkuhcEASRCmEKYKZhGwq3ER0ReiKSVOIyzRkU8EmwhUyKzAwSNyHyL9QZGD4+wDMBLmVEasimFHIiuEKpcHBhwmeQryBMJFohcjuw2s1SBKHZ8BWo/gauyshvobJEYoZAEOSPXnhzwZnAAAAAElFTkSuQmCC",  # nopep8
}
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


def _calc_value(value: int, min_value: int, max_value: int) -> int:
    try:
        if value is not None:
            new_value = int((int(value) / _PIXEL_WIDTH) + _OFFSET)
            # return value inside min and max
            return min(max_value, max(min_value, new_value))

    except (ZeroDivisionError, ValueError):
        pass

    return min_value or 0


def _calc_point(
    x: int, y: int, image_box: tuple[int, int, int, int] | None
) -> tuple[int, int]:
    if image_box is None:
        image_box = (0, 0, x, y)

    return (
        _calc_value(x, image_box[0], image_box[2]),
        _calc_value(y, image_box[1], image_box[3]),
    )


def _draw_positions(
    positions: list[Position], image: Image, image_box: tuple[int, int, int, int]
) -> None:
    for position in positions:
        icon = Image.open(BytesIO(base64.b64decode(_POSITION_PNG[position.type])))
        image.paste(
            icon,
            _calc_point(position.x, position.y, image_box),
            icon.convert("RGBA"),
        )


def _draw_subset(
    subset: MapSubsetEvent,
    draw: "DashedImageDraw",
    image_box: tuple[int, int, int, int],
) -> None:
    coordinates_ = ast.literal_eval(subset.coordinates)
    points: list[tuple[int, int]] = []
    for i in range(0, len(coordinates_), 2):
        points.append(_calc_point(coordinates_[i], coordinates_[i + 1], image_box))

    if len(points) == 4:
        # close rectangle
        points.append(points[0])

    draw.dashed_line(points, dash=(3, 2), fill=_COLORS[subset.type], width=1)


class Map:
    """Map representation."""

    RESIZE_FACTOR = 3

    def __init__(
        self,
        execute_command: Callable[[Command], Coroutine[Any, Any, None]],
        event_bus: EventBus,
    ):
        self._execute_command = execute_command
        self._event_bus = event_bus

        self._map_data: Final[MapData] = MapData()
        self._amount_rooms: int = 0
        self._last_image: LastImage | None = None
        self._listeners: list[EventListener] = []

        async def on_map_set(event: MapSetEvent) -> None:
            if event.type == MapSetType.ROOMS:
                self._amount_rooms = len(event.subsets)
                for room_id, _ in self._map_data.rooms.copy().items():
                    if room_id not in event.subsets:
                        self._map_data.rooms.pop(room_id, None)
            else:
                for subset_id, subset in self._map_data.map_subsets.copy().items():
                    if subset.type == event.type and subset_id not in event.subsets:
                        self._map_data.map_subsets.pop(subset_id, None)

        self._event_bus.subscribe(MapSetEvent, on_map_set)

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

        self._event_bus.subscribe(MapSubsetEvent, on_map_subset)

    # ---------------------------- METHODS ----------------------------

    def _update_trace_points(self, data: str) -> None:
        _LOGGER.debug("[_update_trace_points] Begin")
        trace_points = _decompress_7z_base64_data(data)

        for i in range(0, len(trace_points), 5):
            byte_position_x = struct.unpack("<h", trace_points[i : i + 2])
            byte_position_y = struct.unpack("<h", trace_points[i + 2 : i + 4])

            # Add To List
            position_x = (int(byte_position_x[0] / 5)) + 400
            position_y = (int(byte_position_y[0] / 5)) + 400

            self._map_data.trace_values.append(position_x)
            self._map_data.trace_values.append(position_y)

        _LOGGER.debug("[_update_trace_points] finish")

    def _draw_map_pieces(self, draw: ImageDraw.Draw) -> None:
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

    def enable(self) -> None:
        """Enable map."""
        if self._listeners:
            return

        asyncio.create_task(self._execute_command(GetCachedMapInfo()))

        async def on_position(event: PositionsEvent) -> None:
            self._map_data.positions = event.positions

        self._listeners.append(self._event_bus.subscribe(PositionsEvent, on_position))

        async def on_map_trace(event: MapTraceEvent) -> None:
            if event.start == 0:
                self._map_data.trace_values.clear()

            self._update_trace_points(event.data)

        self._listeners.append(self._event_bus.subscribe(MapTraceEvent, on_map_trace))

        async def on_major_map(event: MajorMapEvent) -> None:
            tasks = []
            for idx, value in enumerate(event.values):
                if (
                    self._map_data.map_pieces[idx].crc32_indicates_update(value)
                    and event.requested
                ):
                    tasks.append(
                        asyncio.create_task(
                            self._execute_command(
                                GetMinorMap(map_id=event.map_id, piece_index=idx)
                            )
                        )
                    )

            if tasks:
                await asyncio.gather(*tasks)

        self._listeners.append(self._event_bus.subscribe(MajorMapEvent, on_major_map))

        async def on_minor_map(event: MinorMapEvent) -> None:
            self._map_data.map_pieces[event.index].update_points(event.value)

        self._listeners.append(self._event_bus.subscribe(MinorMapEvent, on_minor_map))

    def disable(self) -> None:
        """Disable map."""
        listeners = self._listeners
        self._listeners.clear()
        for listener in listeners:
            listener.unsubscribe()

    def refresh(self) -> None:
        """Manually refresh map."""
        if not self._listeners:
            raise MapError("Please enable the map first")

        # todo make it nice pylint: disable=fixme
        self._event_bus.request_refresh(PositionsEvent)
        self._event_bus.request_refresh(MapTraceEvent)
        self._event_bus.request_refresh(MajorMapEvent)

    def get_base64_map(self, width: int | None = None) -> bytes:
        """Return map as base64 image string."""
        if not self._listeners:
            raise MapError("Please enable the map first")

        if (
            self._last_image is not None
            and width == self._last_image.width
            and not self._map_data.changed
        ):
            _LOGGER.debug("[get_base64_map] No need to update")
            return self._last_image.base64_image

        _LOGGER.debug("[get_base64_map] Begin")
        image = Image.new("RGBA", (6400, 6400))
        draw = DashedImageDraw(image)

        self._draw_map_pieces(draw)

        # Draw Trace Route
        if len(self._map_data.trace_values) > 0:
            _LOGGER.debug("[get_base64_map] Draw Trace")
            draw.line(self._map_data.trace_values, fill=_COLORS[_TRACE_MAP], width=1)

        image_box = image.getbbox()
        for subset in self._map_data.map_subsets.values():
            _draw_subset(subset, draw, image_box)

        del draw

        _draw_positions(self._map_data.positions, image, image_box)

        _LOGGER.debug("[get_base64_map] Crop Image")
        cropped = image.crop(image_box)
        del image

        _LOGGER.debug("[get_base64_map] Flipping Image")
        cropped = ImageOps.flip(cropped)

        _LOGGER.debug(
            "[get_base64_map] Map current Size: X: %d Y: %d",
            cropped.size[0],
            cropped.size[1],
        )

        new_size = None
        if width is not None and width > 0:
            height = int((width / cropped.size[0]) * cropped.size[1])
            _LOGGER.debug(
                "[get_base64_map] Resize based on the requested width: %d and calculated height %d",
                width,
                height,
            )
            new_size = (width, height)
        elif cropped.size[0] > 400 or cropped.size[1] > 400:
            _LOGGER.debug(
                "[get_base64_map] Resize disabled.. map over 400 and image width was passed"
            )
        else:
            resize_factor = Map.RESIZE_FACTOR
            _LOGGER.debug("[get_base64_map] Resize factor: %d", resize_factor)
            new_size = (
                cropped.size[0] * resize_factor,
                cropped.size[1] * resize_factor,
            )

        if new_size is not None:
            cropped = cropped.resize(new_size, Image.NEAREST)

        _LOGGER.debug("[get_base64_map] Saving to buffer")
        buffered = BytesIO()
        cropped.save(buffered, format="PNG")
        del cropped

        base64_image = base64.b64encode(buffered.getvalue())
        self._map_data.reset_changed()
        self._last_image = LastImage(base64_image, width)
        _LOGGER.debug("[get_base64_map] Finish")

        return base64_image


class MapPiece:
    """Map piece representation."""

    _NOT_INUSE_CRC32: int = 1295764014

    def __init__(self, on_change: Callable[[], None], index: int) -> None:
        self._on_change = on_change
        self._index = index
        self._points: ndarray | None = None
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
    def points(self) -> ndarray:
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


class DashedImageDraw(ImageDraw.ImageDraw):  # type: ignore
    """Class extend ImageDraw by dashed line."""

    # pylint: disable=invalid-name
    # Copied from https://stackoverflow.com/a/65893631 Credits ands

    def _thick_line(
        self,
        xy: list[tuple[int, int]],
        direction: list[tuple[int, int]],
        fill: tuple | str | None = None,
        width: int = 0,
    ) -> None:
        if xy[0] != xy[1]:
            self.line(xy, fill=fill, width=width)
        else:
            x1, y1 = xy[0]
            delta_x = direction[1][0] - direction[0][0]
            delta_y = direction[1][1] - direction[0][1]

            if delta_x < 0:
                y1 -= 1

            if delta_y < 0:
                x1 -= 1

            if delta_y != 0:
                if delta_x != 0:
                    k = -delta_x / delta_y
                    a = 1 / math.sqrt(1 + k**2)
                    b = (width * a - 1) / 2
                else:
                    k = 0
                    b = (width - 1) / 2
                x1 = x1 - math.floor(b)
                y1 = y1 - int(k * b)
                x2 = x1 + math.ceil(b)
                y2 = y1 + int(k * b)
            else:
                y1 = y1 - math.floor((width - 1) / 2)
                x2 = x1
                y2 = y1 + math.ceil((width - 1) / 2)
            self.line([(x1, y1), (x2, y2)], fill=fill, width=1)

    def dashed_line(
        self,
        xy: list[tuple[int, int]],
        dash: tuple = (2, 2),
        fill: tuple | str | None = None,
        width: int = 0,
    ) -> None:
        """Draw a dashed line, or a connected sequence of line segments."""
        # pylint: disable=too-many-locals
        for i in range(len(xy) - 1):
            x1, y1 = xy[i]
            x2, y2 = xy[i + 1]
            x_length = x2 - x1
            y_length = y2 - y1
            length = math.sqrt(x_length**2 + y_length**2)
            dash_enabled = True
            position = 0
            while position <= length:
                for dash_step in dash:
                    if dash_enabled:
                        start = position / length
                        end = min((position + dash_step - 1) / length, 1)
                        self._thick_line(
                            [
                                (
                                    round(x1 + start * x_length),
                                    round(y1 + start * y_length),
                                ),
                                (
                                    round(x1 + end * x_length),
                                    round(y1 + end * y_length),
                                ),
                            ],
                            xy,
                            fill,
                            width,
                        )
                    dash_enabled = not dash_enabled
                    position += dash_step


@dataclasses.dataclass(frozen=True)
class LastImage:
    """Last created image."""

    base64_image: bytes
    width: int | None


class MapData:
    """Map data."""

    def __init__(self) -> None:
        self._changed: bool = False

        def on_change() -> None:
            self._changed = True

        self._on_change = on_change
        self._map_pieces: OnChangedList[MapPiece] = OnChangedList(
            on_change, [MapPiece(on_change, i) for i in range(64)]
        )
        self._map_subsets: OnChangedDict[int, MapSubsetEvent] = OnChangedDict(on_change)
        self._positions: OnChangedList[Position] = OnChangedList(on_change)
        self._rooms: OnChangedDict[int, Room] = OnChangedDict(on_change)
        self._trace_values: OnChangedList[int] = OnChangedList(on_change)

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
    def trace_values(self) -> OnChangedList[int]:
        """Return trace values."""
        return self._trace_values

    def reset_changed(self) -> None:
        """Reset changed value."""
        self._changed = False
