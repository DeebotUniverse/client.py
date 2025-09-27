from __future__ import annotations

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.json import (
    GetCachedMapInfo,
    GetMapSet,
)
from deebot_client.commands.json.map import GetMapSetV2
from deebot_client.events import MapSetType
from deebot_client.events.map import CachedMapInfoEvent, Map
from deebot_client.message import HandlingState
from tests.commands.json import assert_command
from tests.helpers import get_request_json, get_success_body


@pytest.mark.parametrize(
    ("device_class", "map_set_type"),
    [
        ("yna5xi", GetMapSet),
        ("kr0277", GetMapSetV2),
    ],
)
async def test_getCachedMapInfo(
    device_class: str, map_set_type: type[GetMapSet | GetMapSetV2]
) -> None:
    expected_mid = "199390082"
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
            *[firmware_event for _ in MapSetType],
        ],
        command_result=CommandResult(
            HandlingState.SUCCESS,
            {"map_id": expected_mid},
            [map_set_type(expected_mid, entry) for entry in MapSetType],
        ),
        device_class=device_class,
    )
