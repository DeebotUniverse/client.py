"""Map module."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

import svg

from deebot_client.events.map import CachedMapInfoEvent, MapChangedEvent
from deebot_client.rs.map import PositionType
from deebot_client.rs.util import decompress_base64_data

from .events import (
    MajorMapEvent,
    MapInfoV2Event,
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
from .util import (
    OnChangedDict,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .capabilities import CapabilityMap
    from .device import DeviceCommandExecute
    from .event_bus import EventBus

_LOGGER = get_logger(__name__)


class Map:
    """Map representation."""

    def __init__(
        self,
        execute_command: DeviceCommandExecute,
        event_bus: EventBus,
        capabilities: CapabilityMap,
    ) -> None:
        self._execute_command = execute_command
        self._event_bus = event_bus

        self._capabilities = capabilities
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

    async def _on_first_map_changed_subscription(self) -> Callable[[], None]:
        """On first MapChanged subscription."""
        unsubscribers = []

        async def on_major_map(event: MajorMapEvent) -> None:
            async with asyncio.TaskGroup() as tg:
                for idx, value in enumerate(event.values):
                    if (
                        self._map_data.map_piece_crc32_indicates_update(idx, value)
                        and event.requested
                    ):
                        tg.create_task(
                            self._execute_command(
                                self._capabilities.minor.execute(idx, event.map_id)
                            )
                        )

        unsubscribers.append(self._event_bus.subscribe(MajorMapEvent, on_major_map))

        async def on_minor_map(event: MinorMapEvent) -> None:
            self._map_data.update_map_piece(event.index, event.value)

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
            self._map_data.update_positions(event.positions)

        unsubscribers.append(self._event_bus.subscribe(PositionsEvent, on_position))

        async def on_map_trace(event: MapTraceEvent) -> None:
            if event.start == 0:
                self._map_data.clear_trace_points()

            if data := event.data.strip():
                self._map_data.add_trace_points(data)

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

        self._last_image = self._map_data.generate_svg()
        _LOGGER.debug("[get_svg_map] Finish")
        return self._last_image

    async def teardown(self) -> None:
        """Teardown map."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()


class MapV2:
    """Map V2 representation."""

    def __init__(
        self,
        execute_command: DeviceCommandExecute,
        event_bus: EventBus,
        capabilities: CapabilityMap,
    ) -> None:
        self._execute_command = execute_command
        self._event_bus = event_bus

        self._capabilities = capabilities
        self._unsubscribers: list[Callable[[], None]] = []
        self._rooms: dict[int, Room] = {}
        self._map_info_v2: dict[int, dict[int, list[dict[str, int]]]] = {}
        self._positions: list[Position] = []
        self._traces: list[dict[str, int]] = []

        async def on_major_map(event: MajorMapEvent) -> None:
            if self._capabilities.map_info:
                await self._execute_command(
                    self._capabilities.map_info.execute(event.map_id)
                )

        self._unsubscribers.append(event_bus.subscribe(MajorMapEvent, on_major_map))

        async def on_map_info_v2(event: MapInfoV2Event) -> None:
            rooms = {}
            for room in event.coordinates_map[0][1:]:
                subset_id = room.split(";")[0]
                room_coordinates = room[len(subset_id) + 1 :]
                room_name = (
                    self._rooms[int(subset_id)].name
                    if int(subset_id) in self._rooms
                    else f"Room {subset_id}"  # TODO get from MapSet_V2
                )
                rooms[int(subset_id)] = Room(
                    room_name,
                    int(subset_id),
                    room_coordinates,
                )
            self._rooms = rooms

            def parse_coordinates(
                coordinates: str,
            ) -> tuple[int, list[dict[str, int]]]:
                """Parse coordinates from a string."""
                coords_split = coordinates.strip().split(";")
                room_id = int(coords_split[0])
                coords_str = coords_split[1:] if len(coords_split) > 1 else []
                coords = []
                for coord in coords_str:
                    c_s = coord.split(",")
                    coords.append(
                        {
                            "x": int(c_s[0]),
                            "y": int(c_s[1]),
                        }
                    )
                return (room_id, coords)

            self._map_info_v2 = {}
            for type in event.coordinates_map:
                self._map_info_v2[int(type[0])] = {}
                for room_data in type[1:]:
                    room_id, room_coords = parse_coordinates(room_data)
                    self._map_info_v2[int(type[0])][room_id] = room_coords

            self._event_bus.notify(RoomsEvent(list(self._rooms.values())))
            self._event_bus.notify(MapChangedEvent(datetime.now(UTC)), debounce_time=1)

        self._unsubscribers.append(event_bus.subscribe(MapInfoV2Event, on_map_info_v2))

        async def on_position(event: PositionsEvent) -> None:
            self._positions = event.positions
            self._event_bus.notify(MapChangedEvent(datetime.now(UTC)), debounce_time=1)

        self._unsubscribers.append(event_bus.subscribe(PositionsEvent, on_position))

        async def on_trace(event: MapTraceEvent) -> None:
            if event.start == 0:
                self._traces.clear()
            decompressed_data = decompress_base64_data(event.data.strip())
            for chunk_start in range(0, len(decompressed_data), 5):
                chunk = decompressed_data[chunk_start : chunk_start + 5]
                if len(chunk) < 5:
                    break
                x = int.from_bytes(chunk[0:2], "little", signed=True)
                y = int.from_bytes(chunk[2:4], "little", signed=True)
                connected = (chunk[4] >> 7) == 0
                self._traces.append(
                    {
                        "x": x,
                        "y": y,
                        "connected": connected,
                    }
                )
            self._event_bus.notify(MapChangedEvent(datetime.now(UTC)), debounce_time=1)

        self._unsubscribers.append(event_bus.subscribe(MapTraceEvent, on_trace))

    def refresh(self) -> None:
        """Manually refresh map."""
        self._event_bus.request_refresh(PositionsEvent)
        self._event_bus.request_refresh(MapTraceEvent)
        self._event_bus.request_refresh(MajorMapEvent)

    def get_svg_map(self) -> str | None:
        """Return map as SVG string."""
        if not self._map_info_v2:
            return None

        min_x = 9999999999999999
        min_y = 9999999999999999
        max_x = 0
        max_y = 0
        scale = 0.1

        for type in self._map_info_v2:
            for room_id in self._map_info_v2[type]:
                for coord in self._map_info_v2[type][room_id]:
                    min_x = min(min_x, coord["x"])
                    min_y = min(min_y, coord["y"])
                    max_x = max(max_x, coord["x"])
                    max_y = max(max_y, coord["y"])

        width = int((max_x - min_x) * scale)
        height = int((max_y - min_y) * scale)

        canvas = svg.SVG(
            width=width + 20,
            height=height + 20,
        )
        canvas.elements = [
            svg.Defs(
                elements=[
                    svg.Pattern(
                        id="stripes",
                        patternUnits="userSpaceOnUse",
                        width=10,
                        height=10,
                        elements=[
                            svg.Path(
                                d="M0,10 L10,0",
                                stroke="grey",
                                stroke_width=2,
                            )
                        ],
                    )
                ]
            )
        ]

        def translate_coordinates(x: int, y: int) -> tuple[int, int]:
            """Translate coordinates to fit the canvas."""
            return (
                width - int((x - min_x) * scale) + 10,
                int((y - min_y) * scale) + 10,
            )

        room_colors = ["#9cbdeb", "#f2cf91", "#8ad6dc", "#f3c4c8"]
        for type in self._map_info_v2:
            for room_id in self._map_info_v2[type]:
                canvas.elements.append(
                    svg.Polyline(
                        points=[
                            a
                            for coord in self._map_info_v2[type][room_id]
                            for a in translate_coordinates(coord["x"], coord["y"])
                        ],
                        fill="none"
                        if type not in [1, 6]
                        else room_colors[room_id % len(room_colors)],
                        stroke="black",
                        stroke_width=2,
                    )
                )
                if type == 1:
                    canvas.elements.append(
                        svg.Polyline(
                            points=[
                                a
                                for coord in self._map_info_v2[type][room_id]
                                for a in translate_coordinates(coord["x"], coord["y"])
                            ],
                            fill="url(#stripes)",
                            stroke="none",
                        )
                    )

        if charger_pos := next(
            (pos for pos in self._positions if pos.type == PositionType.CHARGER), None
        ):
            x, y = translate_coordinates(charger_pos.x, charger_pos.y)
            s = 22
            canvas.elements.append(
                svg.Rect(
                    x=x - int(s / 2),
                    y=y - int(s / 2),
                    width=s,
                    height=s,
                    rx=2,
                    ry=2,
                    fill="white",
                    stroke="black",
                    stroke_width=2,
                )
            )
            canvas.elements.append(
                svg.Rect(
                    x=x - int(s / 2) + 3,
                    y=y - int(s / 2) + 3,
                    width=s - 6,
                    height=s - 6,
                    rx=2,
                    ry=2,
                    fill="black",
                )
            )

        if deebot_pos := next(
            iter(pos for pos in self._positions if pos.type == PositionType.DEEBOT),
            None,
        ):
            x, y = translate_coordinates(deebot_pos.x, deebot_pos.y)
            r = 9
            canvas.elements.append(
                svg.Circle(
                    cx=x,
                    cy=y,
                    r=r,
                    fill="white",
                    stroke="black",
                    stroke_width=2,
                )
            )
            canvas.elements.append(
                svg.Circle(
                    cx=x,
                    cy=y,
                    r=r - 3,
                    fill="black",
                )
            )

        return str(canvas)

    async def teardown(self) -> None:
        """Teardown map."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()


class MapData:
    """Map data."""

    def __init__(self, event_bus: EventBus) -> None:
        self._changed: bool = False

        def on_change() -> None:
            self._changed = True
            event_bus.notify(MapChangedEvent(datetime.now(UTC)), debounce_time=1)

        self._on_change = on_change
        self._map_subsets: OnChangedDict[int, MapSubsetEvent] = OnChangedDict(on_change)
        self._positions: list[Position] = []
        self._rooms: OnChangedDict[int, Room] = OnChangedDict(on_change)
        self._data = MapDataRs()

    @property
    def changed(self) -> bool:
        """Indicate if data was changed."""
        return self._changed

    @property
    def map_subsets(self) -> dict[int, MapSubsetEvent]:
        """Return map subsets."""
        return self._map_subsets

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

    def update_positions(self, value: list[Position]) -> None:
        """Update positions."""
        self._positions = value
        self._on_change()

    def update_map_piece(self, index: int, base64_data: str) -> None:
        """Update map piece."""
        if self._data.update_map_piece(index, base64_data):
            self._on_change()

    def map_piece_crc32_indicates_update(self, index: int, crc32: int) -> bool:
        """Return True if update is required."""
        return self._data.map_piece_crc32_indicates_update(index, crc32)

    def generate_svg(self) -> str | None:
        """Generate SVG image."""
        return self._data.generate_svg(
            list(self._map_subsets.values()), self._positions
        )
