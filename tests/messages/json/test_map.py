from __future__ import annotations

from unittest.mock import Mock

import pytest

from deebot_client.event_bus import EventBus
from deebot_client.events.map import MapSetType
from deebot_client.message import HandlingState
from deebot_client.messages.json import OnMapSetV2


@pytest.mark.parametrize(
    ("mid", "type"),
    [
        ("199390082", MapSetType.ROOMS),
        ("199390082", MapSetType.NO_MOP_ZONES),
        ("199390082", MapSetType.VIRTUAL_WALLS),
    ],
)
def test_onMapSetV2(mid: str, type: MapSetType) -> None:
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
