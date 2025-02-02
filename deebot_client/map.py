"""Map module."""

from __future__ import annotations

import asyncio
import dataclasses
from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING, Final
import zlib

from PIL import Image, ImageColor, ImageOps, ImagePalette

from deebot_client.events.map import CachedMapInfoEvent, MapChangedEvent

from .commands.json import GetMinorMap
from .events import (
    MajorMapEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
    Position,
    PositionsEvent,
    RoomsEvent,
)
from .exceptions import MapError
from .logging_filter import get_logger
from .models import Room
from .rs.map import MapData as MapDataRs
from .rs.util import decompress_7z_base64_data
from .util import (
    OnChangedDict,
    OnChangedList,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .device import DeviceCommandExecute
    from .event_bus import EventBus


_LOGGER = get_logger(__name__)


_OFFSET = 400
_DEFAULT_MAP_BACKGROUND_COLOR = ImageColor.getrgb("#badaff")  # floor
_MAP_BACKGROUND_COLORS: dict[int, tuple[int, ...]] = {
    0: ImageColor.getrgb("#000000"),  # unknown (will be transparent)
    1: _DEFAULT_MAP_BACKGROUND_COLOR,  # floor
    2: ImageColor.getrgb("#4e96e2"),  # wall
    3: ImageColor.getrgb("#1a81ed"),  # carpet
    4: ImageColor.getrgb("#dee9fb"),  # not scanned space
    5: ImageColor.getrgb("#edf3fb"),  # possible obstacle
    # fallback to _DEFAULT_MAP_BACKGROUND_COLOR for any other value
}


@dataclasses.dataclass
class BackgroundImage:
    """Background image."""

    bounding_box: tuple[float, float, float, float]
    image: bytes


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
        execute_command: DeviceCommandExecute,
        event_bus: EventBus,
    ) -> None:
        self._execute_command = execute_command
        self._event_bus = event_bus

        self._map_data: Final[MapData] = MapData(event_bus)
        self._amount_rooms: int = 0
        self._last_image: str | None = None
        self._unsubscribers: list[Callable[[], None]] = []

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

        self._unsubscribers.append(event_bus.subscribe(MapSetEvent, on_map_set))

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

        self._unsubscribers.append(event_bus.subscribe(MapSubsetEvent, on_map_subset))

        self._unsubscribers.append(
            event_bus.add_on_subscription_callback(
                MapChangedEvent, self._on_first_map_changed_subscription
            )
        )

    # ---------------------------- METHODS ----------------------------

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

    async def _on_first_map_changed_subscription(self) -> Callable[[], None]:
        """On first MapChanged subscription."""
        unsubscribers = []

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

        unsubscribers.append(self._event_bus.subscribe(MajorMapEvent, on_major_map))

        async def on_minor_map(event: MinorMapEvent) -> None:
            self._map_data.map_pieces[event.index].update_points(event.value)

        unsubscribers.append(self._event_bus.subscribe(MinorMapEvent, on_minor_map))

        async def on_cached_info(_: CachedMapInfoEvent) -> None:
            # We need to subscribe to it, otherwise it could happen
            # that the required MapSet Events are not get
            pass

        cached_map_subscribers = self._event_bus.has_subscribers(CachedMapInfoEvent)
        unsubscribers.append(
            self._event_bus.subscribe(CachedMapInfoEvent, on_cached_info)
        )
        if cached_map_subscribers:
            # Request update only if there was already a subscriber before
            self._event_bus.request_refresh(CachedMapInfoEvent)

        async def on_position(event: PositionsEvent) -> None:
            self._map_data.positions = event.positions

        unsubscribers.append(self._event_bus.subscribe(PositionsEvent, on_position))

        async def on_map_trace(event: MapTraceEvent) -> None:
            if event.start == 0:
                self._map_data.clear_trace_points()

            self._map_data.add_trace_points(event.data)

        unsubscribers.append(self._event_bus.subscribe(MapTraceEvent, on_map_trace))

        def unsub() -> None:
            for unsub in unsubscribers:
                unsub()

        return unsub

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

    def get_svg_map(self) -> str | None:
        """Return map as SVG string."""
        if not self._unsubscribers:
            raise MapError("Please enable the map first")

        if self._last_image and not self._map_data.changed:
            _LOGGER.debug("[get_svg_map] No need to update")
            return self._last_image

        _LOGGER.debug("[get_svg_map] Begin")

        # Reset change before starting to build the SVG
        self._map_data.reset_changed()

        background = self._get_background_image()
        if background is None:
            self._last_image = None
            return None

        self._last_image = self._map_data.generate_svg(
            (
                background.bounding_box[0] - _OFFSET,
                _OFFSET - background.bounding_box[3],
                (background.bounding_box[2] - background.bounding_box[0]),
                (background.bounding_box[3] - background.bounding_box[1]),
            ),
            background.image,
        )
        _LOGGER.debug("[get_svg_map] Finish")
        return self._last_image

    async def teardown(self) -> None:
        """Teardown map."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()


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
        decoded = decompress_7z_base64_data(base64_data)
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
        self._data = MapDataRs()

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

    def reset_changed(self) -> None:
        """Reset changed value."""
        self._changed = False

    def add_trace_points(self, value: str) -> None:
        """Add trace points to the map data."""
        self._data.add_trace_points(value)
        self._on_change()

    def clear_trace_points(self) -> None:
        """Clear trace points."""
        self._data.clear_trace_points()
        self._on_change()

    def generate_svg(
        self,
        viewbox: tuple[float, float, float, float],
        image: bytes,
    ) -> str:
        """Generate SVG image."""
        return self._data.generate_svg(
            viewbox, image, list(self._map_subsets.values()), self._positions
        )
