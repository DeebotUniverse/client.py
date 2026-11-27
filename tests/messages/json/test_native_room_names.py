"""Unnamed native rooms need distinct labels without changing device metadata."""

from __future__ import annotations

from unittest.mock import AsyncMock

from deebot_client.event_bus import EventBus
from deebot_client.events import RoomsEvent
from deebot_client.hardware.cqyi87 import get_device_info
from deebot_client.messages.json.native_map import OnNativeMapReport


def test_unnamed_rooms_get_id_labels_and_real_names_survive() -> None:
    bus = EventBus(AsyncMock(), get_device_info().capabilities)
    OnNativeMapReport.handle(
        bus,
        {
            "body": {
                "data": {
                    "mapId": "1",
                    "areas": [
                        {"id": 2, "name": "", "type": ""},
                        {"id": 3, "name": "", "type": ""},
                        {"id": 5, "name": "Kitchen"},
                    ],
                }
            }
        },
    )
    event = bus.get_last_event(RoomsEvent)
    assert event is not None
    assert [(room.id, room.name) for room in event.rooms] == [
        (2, "Room 2"),
        (3, "Room 3"),
        (5, "Kitchen"),
    ]
