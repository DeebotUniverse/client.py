from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.commands.json import (
    GetCachedMapInfo,
    GetMapInfoV2,
    GetMapSet,
)
from deebot_client.commands.json.map import GetMapSetV2
from deebot_client.events import MapSetType
from deebot_client.events.map import CachedMapInfoEvent, Map
from deebot_client.hardware import get_static_device_info
from deebot_client.message import HandlingResult, HandlingState
from tests.commands.json import assert_command
from tests.helpers import get_request_json, get_success_body

if TYPE_CHECKING:
    from deebot_client.command import Command


@pytest.mark.parametrize(
    ("device_class", "map_set_type"),
    [
        ("yna5xi", GetMapSet),
        ("kr0277", GetMapSetV2),
        ("lwmdoj", GetMapSetV2),
    ],
)
async def test_getCachedMapInfo(
    device_class: str,
    map_set_type: type[GetMapSet | GetMapSetV2],
) -> None:
    expected_mid = "199390082"
    static_device_info = await get_static_device_info(device_class)
    assert static_device_info
    assert static_device_info.capabilities.map
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "enable": 1,
                "info": [
                    {
                        "mid": expected_mid,
                        "index": 0,
                        "status": 1,
                        "using": 1,
                        "built": 1,
                        "name": "Erdgeschoss",
                    },
                    {
                        "mid": "722607162",
                        "index": 3,
                        "status": 0,
                        "using": 0,
                        "built": 0,
                        "name": "",
                    },
                    {
                        "mid": "722607178",
                        "index": 3,
                        "status": 0,
                        "using": 0,
                        "built": 1,
                        "name": "",
                    },
                ],
            }
        )
    )
    expected_commands: list[Command] = [
        map_set_type(expected_mid, entry) for entry in MapSetType
    ]
    if static_device_info.capabilities.map.info:
        expected_commands.append(GetMapInfoV2(expected_mid))
    await assert_command(
        GetCachedMapInfo(),
        json,
        [
            firmware_event,
            CachedMapInfoEvent(
                {
                    Map(
                        id=expected_mid,
                        name="Erdgeschoss",
                        using=True,
                        built=True,
                    ),
                    Map(
                        id="722607162",
                        name="",
                        using=False,
                        built=False,
                    ),
                    Map(
                        id="722607178",
                        name="",
                        using=False,
                        built=True,
                    ),
                }
            ),
            *[firmware_event for _ in expected_commands],
        ],
        handling_result=HandlingResult(
            HandlingState.SUCCESS,
            {"map_id": expected_mid},
            expected_commands,
        ),
        device_class=device_class,
    )
