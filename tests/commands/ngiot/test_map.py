from __future__ import annotations

from unittest.mock import Mock, call

import pytest

from deebot_client.commands.ngiot.map import GetCachedMapInfo, GetMapSet
from deebot_client.event_bus import EventBus
from deebot_client.events.map import CachedMapInfoEvent, Map, MapSetType
from deebot_client.hardware import get_static_device_info
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.rs.map import RotationAngle


@pytest.mark.asyncio
async def test_getCachedMapInfo_bootstraps_map_sets() -> None:
    static_device_info = await get_static_device_info("eyfj07")
    assert static_device_info is not None
    assert static_device_info.capabilities.map is not None

    event_bus = Mock(spec_set=EventBus)
    event_bus.capabilities = static_device_info.capabilities

    response = {
        "ret": "ok",
        "resp": {
            "body": {
                "data": {
                    "mapInfos": [
                        {
                            "mapId": "3",
                            "name": "Home",
                            "status": 1,
                            "angle": 90,
                        },
                        {
                            "mapId": "4",
                            "name": "Upstairs",
                            "status": 0,
                            "angle": 0,
                        },
                    ]
                }
            }
        },
    }

    result = GetCachedMapInfo()._handle_response(event_bus, response)

    assert result == HandlingResult(
        HandlingState.SUCCESS,
        {"map_id": "3"},
        [GetMapSet("3", entry) for entry in MapSetType],
    )
    event_bus.notify.assert_has_calls(
        [
            call(
                CachedMapInfoEvent(
                    maps={
                        Map(
                            id="3",
                            name="Home",
                            using=True,
                            built=True,
                            angle=RotationAngle.DEG_90,
                        ),
                        Map(
                            id="4",
                            name="Upstairs",
                            using=False,
                            built=True,
                            angle=RotationAngle.DEG_0,
                        ),
                    }
                )
            )
        ]
    )
    assert event_bus.notify.call_count == 1
