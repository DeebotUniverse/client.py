from __future__ import annotations

from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import CleanAreaV2, CleanV2, GetCleanInfoV2
from deebot_client.commands.json.map import GetMapInfoV2, GetMapSetV2
from deebot_client.commands.json.work_state import GetWorkState
from deebot_client.events import LifeSpan
from deebot_client.hardware.ulzked import get_device_info


def test_ulzked_uses_v2_capabilities() -> None:
    capabilities = get_device_info().capabilities

    assert capabilities.clean.action.command is CleanV2
    assert capabilities.clean.action.area is CleanAreaV2
    assert capabilities.state.get == [
        GetChargeState(),
        GetCleanInfoV2(),
        GetWorkState(),
    ]

    assert capabilities.map is not None
    assert capabilities.map.info is not None
    assert capabilities.map.info.execute is GetMapInfoV2
    assert capabilities.map.set.execute is GetMapSetV2

    assert capabilities.station is not None
    assert capabilities.station.state.get == [GetWorkState()]
    assert capabilities.life_span.types == (
        LifeSpan.BRUSH,
        LifeSpan.CLEANING_SOLUTION,
        LifeSpan.DUST_BAG,
        LifeSpan.HAND_FILTER,
        LifeSpan.FILTER,
        LifeSpan.ROUND_MOP,
        LifeSpan.SEWAGE_BOX,
        LifeSpan.SIDE_BRUSH,
        LifeSpan.STRAINER,
        LifeSpan.UNIT_CARE,
        LifeSpan.WATER_SINK,
    )
