"""Map module."""
import asyncio
import base64
import logging
import lzma
import struct
from io import BytesIO
from typing import Any, Awaitable, Callable, Dict, Final, List, Optional

from numpy import ndarray, reshape, zeros
from PIL import Image, ImageDraw, ImageOps

from .command import Command
from .commands import (
    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapSubSet,
    GetMapTrace,
    GetMinorMap,
)
from .events import (
    MapEventDto,
    Position,
    PositionsEventDto,
    PositionType,
    RoomsEventDto,
)
from .events.event_bus import EventBus
from .models import Room

_LOGGER = logging.getLogger(__name__)
_TRACE_MAP = "trace_map"
_ROOM_INT_TO_NAME = {
    0: "Default",
    1: "Living Room",
    2: "Dining Room",
    3: "Bedroom",
    4: "Study",
    5: "Kitchen",
    6: "Bathroom",
    7: "Laundry",
    8: "Lounge",
    9: "Storeroom",
    10: "Kids room",
    11: "Sunroom",
    12: "Corridor",
    13: "Balcony",
    14: "Gym",
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


_POSITION_PNG = {
    PositionType.DEEBOT: "iVBORw0KGgoAAAANSUhEUgAAAAYAAAAGCAIAAABvrngfAAAACXBIWXMAAAsTAAALEwEAmpwYAAAF0WlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgNS42LWMxNDUgNzkuMTYzNDk5LCAyMDE4LzA4LzEzLTE2OjQwOjIyICAgICAgICAiPiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtbG5zOnhtcE1NPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvbW0vIiB4bWxuczpzdEV2dD0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL3NUeXBlL1Jlc291cmNlRXZlbnQjIiB4bWxuczpkYz0iaHR0cDovL3B1cmwub3JnL2RjL2VsZW1lbnRzLzEuMS8iIHhtbG5zOnBob3Rvc2hvcD0iaHR0cDovL25zLmFkb2JlLmNvbS9waG90b3Nob3AvMS4wLyIgeG1wOkNyZWF0b3JUb29sPSJBZG9iZSBQaG90b3Nob3AgQ0MgMjAxOSAoV2luZG93cykiIHhtcDpDcmVhdGVEYXRlPSIyMDIwLTA1LTI0VDEyOjAzOjE2KzAyOjAwIiB4bXA6TWV0YWRhdGFEYXRlPSIyMDIwLTA1LTI0VDEyOjAzOjE2KzAyOjAwIiB4bXA6TW9kaWZ5RGF0ZT0iMjAyMC0wNS0yNFQxMjowMzoxNiswMjowMCIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDo0YWM4NWY5MC1hNWMwLTE2NDktYTQ0MC0xMWM0NWY5OGQ1MDYiIHhtcE1NOkRvY3VtZW50SUQ9ImFkb2JlOmRvY2lkOnBob3Rvc2hvcDo3Zjk3MTZjMi1kZDM1LWJiNDItYjMzZS1hYjYwY2Y4ZTZlZDYiIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDpiMzhiNGZlMS1lOGNkLTJjNDctYmQwZC1lNmZiNzRhMjFkMDciIGRjOmZvcm1hdD0iaW1hZ2UvcG5nIiBwaG90b3Nob3A6Q29sb3JNb2RlPSIzIj4gPHhtcE1NOkhpc3Rvcnk+IDxyZGY6U2VxPiA8cmRmOmxpIHN0RXZ0OmFjdGlvbj0iY3JlYXRlZCIgc3RFdnQ6aW5zdGFuY2VJRD0ieG1wLmlpZDpiMzhiNGZlMS1lOGNkLTJjNDctYmQwZC1lNmZiNzRhMjFkMDciIHN0RXZ0OndoZW49IjIwMjAtMDUtMjRUMTI6MDM6MTYrMDI6MDAiIHN0RXZ0OnNvZnR3YXJlQWdlbnQ9IkFkb2JlIFBob3Rvc2hvcCBDQyAyMDE5IChXaW5kb3dzKSIvPiA8cmRmOmxpIHN0RXZ0OmFjdGlvbj0ic2F2ZWQiIHN0RXZ0Omluc3RhbmNlSUQ9InhtcC5paWQ6NGFjODVmOTAtYTVjMC0xNjQ5LWE0NDAtMTFjNDVmOThkNTA2IiBzdEV2dDp3aGVuPSIyMDIwLTA1LTI0VDEyOjAzOjE2KzAyOjAwIiBzdEV2dDpzb2Z0d2FyZUFnZW50PSJBZG9iZSBQaG90b3Nob3AgQ0MgMjAxOSAoV2luZG93cykiIHN0RXZ0OmNoYW5nZWQ9Ii8iLz4gPC9yZGY6U2VxPiA8L3htcE1NOkhpc3Rvcnk+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+AP7+NwAAAFpJREFUCJllzEEKgzAQhtFvMkSsEKj30oUXrYserELA1obhd+nCd4BnksZ53X4Cnr193ov59Iq+o2SA2vz4p/iKkgkRouTYlbhJ/jBqww03avPBTNI4rdtx9ScfWyYCg52e0gAAAABJRU5ErkJggg==",  # nopep8
    PositionType.CHARGER: "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAOCAYAAAAWo42rAAAAdUlEQVQoU2NkQAP/nzD8BwkxyjAwIkuhcEASRCmEKYKZhGwq3ER0ReiKSVOIyzRkU8EmwhUyKzAwSNyHyL9QZGD4+wDMBLmVEasimFHIiuEKpcHBhwmeQryBMJFohcjuw2s1SBKHZ8BWo/gauyshvobJEYoZAEOSPXnhzwZnAAAAAElFTkSuQmCC",  # nopep8
}


def _draw_positions(
    positions: List[Position],
    image: Image,
    pixel_width: int,
    offset: int,
) -> None:
    for position in positions:
        icon = Image.open(BytesIO(base64.b64decode(_POSITION_PNG[position.type])))
        image.paste(
            icon,
            (
                int((position.x / pixel_width) + offset),
                int((position.y / pixel_width) + offset),
            ),
            icon.convert("RGBA"),
        )


def _calc_coordinate(value: Optional[str], pixel_width: int, offset: int) -> float:
    try:
        if value is not None:
            return (int(value) / pixel_width) + offset
    except (ZeroDivisionError, ValueError):
        pass

    return 0.0


class Map:
    """Map representation."""

    COLORS = {
        0x01: "#badaff",  # floor
        0x02: "#4e96e2",  # wall
        0x03: "#1a81ed",  # carpet
        _TRACE_MAP: "#FFFFFF",
    }

    RESIZE_FACTOR = 3
    PIXEL_WIDTH = 50
    OFFSET = 400

    def __init__(
        self, execute_command: Callable[[Command], Awaitable[None]], event_bus: EventBus
    ):
        self._execute_command = execute_command
        self._event_bus = event_bus

        self._positions: List[Position] = []
        self._rooms: Final[Dict[int, Room]] = {}
        self._amount_rooms: int = 0
        self._trace_values: List[int] = []
        self._map_pieces: List[MapPiece] = [MapPiece(i) for i in range(64)]
        self._is_map_up_to_date: bool = False
        self._base64_image: Optional[bytes] = None
        self._last_requested_width: Optional[int] = None

        async def on_position(event: PositionsEventDto) -> None:
            self._positions = event.positions

        event_bus.subscribe(PositionsEventDto, on_position)

    # ---------------------------- EVENT HANDLING ----------------------------

    async def _handle(
        self, command_name: str, message: Dict[str, Any], requested: bool = True
    ) -> None:
        """Handle the given map message. Do not use this method!! Use vacuum_bot methods instead.

        :param command_name: the name of the event or request
        :param message: the message
        :param requested: True if we manual requested the data (ex. via rest). MQTT -> False
        :return: None
        """
        if requested:
            if message.get("ret") != "ok":
                _LOGGER.warning('Event %s where ret != "ok": %s', command_name, message)
                return

            message = message.get("resp", message)

        body = message.get("body", {})

        if not body:
            _LOGGER.warning("Invalid Event %s: %s", command_name, message)
            return

        data = body.get("data", {})

        if command_name == GetCachedMapInfo.name:
            await self._handle_cached_map_info(data, requested)
        elif command_name == GetMapSet.name:
            await self._handle_map_set(data, requested)
        elif command_name == GetMapSubSet.name:
            self._handle_map_sub_set(data)
        elif not self._event_bus.has_subscribers(MapEventDto):
            # above events must be processed always as they are needed to get room information's
            _LOGGER.debug("No Map subscribers. Skipping map events")
            return
        elif command_name == GetMapTrace.name:
            await self._handle_map_trace(data, requested)
        elif command_name == GetMajorMap.name:
            await self._handle_major_map(data, requested)
        elif command_name == GetMinorMap.name:
            self._handle_minor_map(data)
        else:
            _LOGGER.debug('Unknown command "%s" with %s', command_name, message)

    async def _handle_cached_map_info(self, event_data: dict, requested: bool) -> None:
        try:
            map_id: Optional[str] = None
            for map_status in event_data["info"]:
                if map_status["using"] == 1:
                    map_id = map_status["mid"]
                    _LOGGER.debug("[_handle_cached_map] Using Map: %s", map_id)
                    break

            if requested and map_id is not None:
                await self._execute_command(GetMapSet(map_id))
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.debug(ex, exc_info=True)
            _LOGGER.warning(
                "[_handle_cached_map] MapID not found -- did you finish your first auto cleaning?"
            )

    async def _handle_map_set(self, event_data: dict, requested: bool) -> None:
        map_id = event_data["mid"]
        map_set_id = event_data["msid"]
        map_type = event_data["type"]
        subsets = event_data["subsets"]

        self._rooms.clear()
        self._amount_rooms = len(subsets) if subsets else 0

        if requested:
            tasks = []
            for subset in subsets:
                tasks.append(
                    asyncio.create_task(
                        self._execute_command(
                            GetMapSubSet(
                                map_id=map_id,
                                map_set_id=map_set_id,
                                map_type=map_type,
                                map_subset_id=subset["mssid"],
                            )
                        )
                    )
                )

            if tasks:
                await asyncio.gather(*tasks)

    def _handle_map_sub_set(self, event_data: dict) -> None:
        if event_data.get("type", None) != "ar":
            _LOGGER.debug('Currently supporting only type="ar": event=%s', event_data)
            return

        subtype = event_data.get("subtype", event_data.get("subType", None))
        if subtype is None:
            _LOGGER.warning(
                "[_handle_map_sub_set] SubType missing in message %s", event_data
            )
            return

        subtype = int(subtype)
        room = Room(
            subtype=_ROOM_INT_TO_NAME[subtype],
            id=int(event_data["mssid"]),
            coordinates=event_data["value"],
        )
        if self._rooms.get(subtype, None) == room:
            return

        self._rooms[subtype] = room

        if len(self._rooms) == self._amount_rooms:
            self._event_bus.notify(RoomsEventDto(list(self._rooms.values())))

    async def _handle_map_trace(self, event_data: dict, requested: bool) -> None:
        total_count = int(event_data["totalCount"])
        trace_start = int(event_data["traceStart"])

        # No trace value available
        if "traceValue" in event_data:
            if trace_start == 0:
                self._trace_values = []

            self._update_trace_points(event_data["traceValue"])

            trace_start += GetMapTrace.TRACE_POINT_COUNT
            if trace_start < total_count and requested:
                await self._execute_command(GetMapTrace(trace_start))

    async def _handle_major_map(self, event_data: dict, requested: bool) -> None:
        _LOGGER.debug("[_handle_major_map] begin")
        values = event_data["value"].split(",")

        if requested:
            tasks = []
            for i in range(64):
                if self._map_pieces[i].is_update(values[i]):
                    _LOGGER.debug(
                        "[_handle_major_map] MapPiece %d needs to be updated", i
                    )
                    self._is_map_up_to_date = False
                    tasks.append(
                        asyncio.create_task(
                            self._execute_command(
                                GetMinorMap(map_id=event_data["mid"], piece_index=i)
                            )
                        )
                    )
            if tasks:
                await asyncio.gather(*tasks)

    def _handle_minor_map(self, event_data: dict) -> None:
        self._add_map_piece(event_data["pieceIndex"], event_data["pieceValue"])

    # ---------------------------- METHODS ----------------------------

    def _add_map_piece(self, map_piece: int, b64: str) -> None:
        _LOGGER.debug("[AddMapPiece] %d %s", map_piece, b64)

        decoded = _decompress_7z_base64_data(b64)
        points_array = reshape(list(decoded), (100, 100))

        self._map_pieces[map_piece].points = points_array
        _LOGGER.debug("[AddMapPiece] Done")

    def _update_trace_points(self, data: str) -> None:
        _LOGGER.debug("[_update_trace_points] Begin")
        trace_points = _decompress_7z_base64_data(data)

        for i in range(0, len(trace_points), 5):
            byte_position_x = struct.unpack("<h", trace_points[i : i + 2])
            byte_position_y = struct.unpack("<h", trace_points[i + 2 : i + 4])

            # Add To List
            position_x = (int(byte_position_x[0] / 5)) + 400
            position_y = (int(byte_position_y[0] / 5)) + 400

            self._trace_values.append(position_x)
            self._trace_values.append(position_y)

        _LOGGER.debug("[_update_trace_points] finish")

    def _draw_map_pices(self, draw: ImageDraw.Draw) -> None:
        _LOGGER.debug("[_draw_map_pices] Draw")
        image_x = 0
        image_y = 0

        for i in range(64):
            if i > 0:
                if i % 8 != 0:
                    image_y += 100
                else:
                    image_x += 100
                    image_y = 0

            current_piece = self._map_pieces[i]
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
                            raise RuntimeError("Map Limit reached!")
                        if pixel_type in [0x01, 0x02, 0x03]:
                            draw.point((point_x, point_y), fill=Map.COLORS[pixel_type])

    def get_base64_map(self, width: Optional[int] = None) -> bytes:
        """Return map as base64 image string."""
        if (
            self._is_map_up_to_date
            and width == self._last_requested_width
            and self._base64_image is not None
        ):
            _LOGGER.debug("[get_base64_map] No need to update")
            return self._base64_image

        _LOGGER.debug("[get_base64_map] Begin")
        image = Image.new("RGBA", (6400, 6400))
        draw = ImageDraw.Draw(image)

        self._draw_map_pices(draw)

        # Draw Trace Route
        if len(self._trace_values) > 0:
            _LOGGER.debug("[get_base64_map] Draw Trace")
            draw.line(self._trace_values, fill=Map.COLORS[_TRACE_MAP], width=1)

        del draw

        _draw_positions(self._positions, image, Map.PIXEL_WIDTH, Map.OFFSET)

        _LOGGER.debug("[get_base64_map] Crop Image")
        image_box = image.getbbox()
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

        self._is_map_up_to_date = True
        self._last_requested_width = width
        self._base64_image = base64.b64encode(buffered.getvalue())
        _LOGGER.debug("[GetBase64Map] Finish")

        return self._base64_image


class MapPiece:
    """Map piece representation."""

    NOT_INUSE: str = "1295764014"

    def __init__(self, index: int) -> None:
        self._index = index
        self._points: Optional[ndarray] = None
        self._in_use: bool = False
        self._piece: str = MapPiece.NOT_INUSE

    def is_update(self, map_piece: str) -> bool:
        """Return True if update is required."""
        piece = map_piece
        if self._piece != piece:
            self._piece = piece

            if piece == MapPiece.NOT_INUSE:
                self._in_use = False
                return False
            self._in_use = True
            return True

        _LOGGER.debug("No update needed for piece idx %d", self._index)
        return False

    @property
    def in_use(self) -> bool:
        """Return True if piece is in use."""
        return self._in_use

    @property
    def points(self) -> ndarray:
        """I'm the 'x' property."""
        if not self._in_use or self._points is None:
            return zeros((100, 100))
        return self._points

    @points.setter
    def points(self, points: ndarray) -> None:
        self._in_use = True
        self._points = points
