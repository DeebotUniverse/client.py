"""Tests regarding mowing area commands."""

from __future__ import annotations

from unittest.mock import Mock, call

import orjson

from deebot_client.commands.json import GetAreaParameter, GetAreaSet, SetAreaParameter
from deebot_client.commands.json.area_set import GetMowingAreas
from deebot_client.event_bus import EventBus
from deebot_client.events import CachedMapInfoEvent
from deebot_client.events.map import Map
from deebot_client.events.mower import (
    AreaParameter,
    AreaParametersEvent,
    MowingArea,
    MowingAreasEvent,
    ObstacleHeight,
)
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.rs.map import RotationAngle
from tests.helpers import get_message_json, get_request_json, get_success_body

from . import assert_command, assert_execute_command

_AREA_1 = AreaParameter(
    area_id="1", cut_height=4, cut_mode=2, obstacle_height=ObstacleHeight.NORMAL
)
_AREA_2 = AreaParameter(
    area_id="2", cut_height=4, cut_mode=2, obstacle_height=ObstacleHeight.NORMAL
)


async def test_GetAreaParameter() -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "areaParameters": [
                    {
                        "areaID": "1",
                        "mowHeightLevel": 4,
                        "cutMode": 2,
                        "obstacleHeight": 2,
                    },
                    {
                        "areaID": "2",
                        "mowHeightLevel": 4,
                        "cutMode": 2,
                        "obstacleHeight": 2,
                    },
                ]
            }
        )
    )
    await assert_command(
        GetAreaParameter(),
        json,
        (firmware_event, AreaParametersEvent([_AREA_1, _AREA_2])),
    )


async def test_SetAreaParameter() -> None:
    args = {"areaID": "1", "mowHeightLevel": 4, "cutMode": 2, "obstacleHeight": 1}
    command = SetAreaParameter(
        area_id="1", cut_height=4, cut_mode=2, obstacle_height=ObstacleHeight.LOW
    )
    await assert_execute_command(command, args)

    # merge with the last event
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.return_value = AreaParametersEvent([_AREA_1, _AREA_2])
    data, firmware_event = get_message_json(get_success_body())
    command.handle_mqtt_p2p(event_bus, orjson.dumps(data))
    event_bus.notify.assert_has_calls(
        [
            call(firmware_event),
            call(
                AreaParametersEvent(
                    [
                        AreaParameter(
                            area_id="1",
                            cut_height=4,
                            cut_mode=2,
                            obstacle_height=ObstacleHeight.LOW,
                        ),
                        _AREA_2,
                    ]
                )
            ),
        ]
    )

    assert SetAreaParameter.create_from_mqtt(
        orjson.dumps({"body": {"data": args}})
    ) == (command)


_AREA_SET = {
    "mid": "1",
    "aid": "0",
    "type": "ar",
    "subsets": "XQAABABXAAAAAC2WwEIAXhRj1+l1SzycE8xEEhUeTNAPRY/VWExQuvmlvD8Zpe3o6hIbyYoEsmOIhha+apYp0aygAA==",
    "infoSize": 130,
}
_AREAS_EVENT = MowingAreasEvent(
    [
        MowingArea(id="1", name="Vorne", label=(-5300.0, 1500.0)),
        MowingArea(id="2", name="Hinten", label=(-5300.0, 18050.0)),
    ]
)


async def test_GetAreaSet() -> None:
    json, firmware_event = get_request_json(get_success_body(_AREA_SET))
    command = GetAreaSet("1")
    assert command._args == {"mid": "1", "aid": "0", "type": "ar"}
    await assert_command(command, json, (firmware_event, _AREAS_EVENT))


async def test_GetMowingAreas() -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "enable": 0,
                "info": [
                    {
                        "mid": "0",
                        "backupId": "",
                        "status": 1,
                        "index": 3,
                        "using": 0,
                        "built": 0,
                        "name": "",
                    },
                    {
                        "mid": "1",
                        "backupId": "0",
                        "status": 0,
                        "index": 0,
                        "using": 1,
                        "built": 1,
                        "name": "",
                    },
                ],
            }
        )
    )
    area_set_json, _ = get_request_json(get_success_body(_AREA_SET))
    await assert_command(
        GetMowingAreas(),
        (json, area_set_json),
        (
            firmware_event,
            CachedMapInfoEvent(
                maps={
                    Map(
                        id="1",
                        name="",
                        using=True,
                        built=True,
                        angle=RotationAngle.DEG_0,
                    )
                }
            ),
            firmware_event,
            _AREAS_EVENT,
        ),
        device_class="2px96q",
        handling_result=HandlingResult(
            HandlingState.SUCCESS, {"map_id": "1"}, [GetAreaSet("1")]
        ),
        expected_raw_response=json,
    )
