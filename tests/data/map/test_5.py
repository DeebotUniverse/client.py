"""Map of a DEEBOT T80 OMNI: outline version 2, rooms with label positions, furniture and carpets.

The flat is invented, the format is the one sent by the bot.
"""

from __future__ import annotations

from deebot_client.events import RoomsEvent
from deebot_client.events.map import (
    CachedMapInfoEvent,
    Furniture,
    FurnitureEvent,
    Map,
    MapInfoEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    Position,
    PositionsEvent,
)
from deebot_client.models import Room
from deebot_client.rs.map import PositionType, RotationAngle

DEVICE_CLASS = "02qwum"
MAP_ID = "123456789"

EVENTS = [
    CachedMapInfoEvent(
        maps={
            Map(
                id=MAP_ID,
                name="Map 1",
                using=True,
                built=True,
                angle=RotationAngle.DEG_0,
            )
        }
    ),
    PositionsEvent(
        positions=[
            Position(type=PositionType.DEEBOT, x=310, y=3690, a=-92),
            Position(type=PositionType.CHARGER, x=300, y=3700, a=-90),
        ]
    ),
    MapInfoEvent(
        map_id=MAP_ID,
        info="KLUv/WDlAjUJAOIKGQ+wJQ8cWop2b8jOOWhLogRBIHRERKMRjbbtXjT4hDgWeui+38nS7m+9XsEqRo0nfegWYAJ5RboQZaT/3dMXJiN2u/nX1xiWtjcMpWVkjIHpYmUka6VLCg1llaZzdmgoSUYqABB/qJFlp5LCsB3QoqKyDRBIp4SmTQckWY0uGwVlM5pmFVH3GFjZsXb6AdCEiNxSdboT/Qro/pZVazKmhru4fkGhfSuWUPcwa5rY7zy/yDfeoQIMCx0fU1WU42wsl8OUFikF4NWE+0GTGXe5tXHQGvisbS7Wz5z8f84ykbHwt3S2AMKZ6nAURvWXJGLPSsCx5GOX0iZiHWYeyZ6BN7gYeUGH0DljZJFGAJEaemgh798oYburiVIgKfFNgQF84OMUVQ==",
    ),
    RoomsEvent(
        MAP_ID,
        [
            Room("Living room", 0, "", center=(3000, 2000), neighbors=(1, 2)),
            Room("Kitchen", 1, "", center=(7500, 2000), neighbors=(0, 2)),
            Room("Hallway", 2, "", center=(4500, -750), neighbors=(0, 1, 3, 4, 7)),
            Room("Bedroom", 3, "", center=(2000, -3500), neighbors=(2, 4)),
            Room("Bathroom", 4, "", center=(5250, -3500), neighbors=(2, 3, 7)),
            Room("Master bedroom", 7, "", center=(7750, -3500), neighbors=(2, 4)),
        ],
    ),
    MapSubsetEvent(
        id=0,
        type=MapSetType.VIRTUAL_WALLS,
        coordinates="['4500', '3800', '4500', '2800', '5800', '2800', '5800', '3800']",
    ),
    MapSubsetEvent(
        id=1,
        type=MapSetType.VIRTUAL_WALLS,
        coordinates="['6200', '2000', '8800', '2000']",
    ),
    MapSetEvent(MapSetType.VIRTUAL_WALLS, [0, 1], MAP_ID),
    FurnitureEvent(
        MAP_ID,
        [
            Furniture(
                id=0, type=20, coordinates="1000,1000,1000,2600,3400,2600,3400,1000"
            ),
            Furniture(
                id=1, type=20, coordinates="8500,-3000,8500,-4500,9800,-4500,9800,-3000"
            ),
            Furniture(
                id=2, type=8, coordinates="300,-5300,300,-3300,1900,-3300,1900,-5300"
            ),
            Furniture(
                id=3, type=8, coordinates="6800,-5300,6800,-3500,8700,-3500,8700,-5300"
            ),
            Furniture(
                id=4, type=1005, coordinates="8200,3300,8200,3900,8900,3900,8900,3300"
            ),
        ],
    ),
    MapTraceEvent(
        start=0,
        total=33,
        data="XQAAAQBkAAAAABQACYDUX97ABJsOyExb+T32qvhdzi0vjMKGjs8J3QD2Zd0uJWJEj+46P3//96VYAA==",
    ),
    MapTraceEvent(
        start=20,
        total=33,
        data="XQAAAQBBAAAAAFIASJgPhADUv7rFAsZOWWP89RSYFw18o0fDa9llvsjVS5pQphnnrBrn/nuXAA==",
    ),
]
