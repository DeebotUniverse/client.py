from __future__ import annotations

from unittest.mock import Mock

import pytest

from deebot_client.event_bus import EventBus
from deebot_client.events import MajorMapEvent, MapSetType
from deebot_client.message import HandlingState
from deebot_client.messages.json import OnMajorMap, OnMapSetV2
from tests.helpers import get_message_json, get_success_body
from tests.messages import assert_message


async def test_OnPos() -> None:
    expected_mid = "199390082"
    value = "1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,3378526980,2963288214,2739565817,729228561,2452519304,1295764014,1295764014"

    json = get_message_json(get_success_body({"mid": expected_mid, "value": value}))

    assert_message(
        OnMajorMap,
        json,
        MajorMapEvent(expected_mid, value.split(","), requested=True),
    )


@pytest.mark.parametrize(
    ("mid", "type"),
    [
        ("199390082", MapSetType.ROOMS),
        ("199390082", MapSetType.NO_MOP_ZONES),
        ("199390082", MapSetType.VIRTUAL_WALLS),
    ],
)
def test_OnMapSetV2(mid: str, type: MapSetType) -> None:
    data = {
        "header": {
            "pri": 1,
            "tzm": 480,
            "ts": "1304637391896",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
        },
        "body": {"data": {"mid": mid, "type": type.value}},
    }

    # NOTE: this needs to be update when OnMapSetV2 can call commands
    event_bus = Mock(spec_set=EventBus)
    result = OnMapSetV2.handle(event_bus, data)
    assert result.state == HandlingState.SUCCESS
