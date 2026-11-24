from __future__ import annotations

import pytest

from deebot_client import hardware
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import CleanAreaV2, CleanV2
from deebot_client.commands.json.station_state import GetStationState
from deebot_client.commands.json.work_state import GetWorkState
from deebot_client.models import CleanMode


@pytest.mark.parametrize("class_", ["tbeztu", "6v4trk"])
async def test_x12_pro_omni_capabilities(class_: str) -> None:
    info = await hardware.get_static_device_info(class_)
    assert info is not None
    capabilities = info.capabilities

    assert capabilities.clean.action.command is CleanV2
    assert capabilities.state.get == [GetChargeState(), GetWorkState()]
    assert capabilities.station is not None
    assert capabilities.station.state.get == [GetStationState()]


@pytest.mark.parametrize("class_", ["tbeztu", "6v4trk"])
@pytest.mark.parametrize(
    ("mode", "area", "cleanings", "content"),
    [
        (CleanMode.SPOT_AREA, [3], 1, {"type": "freeClean", "value": "1,3"}),
        (CleanMode.SPOT_AREA, [0, 3], 1, {"type": "freeClean", "value": "1,0;1,3"}),
        (
            CleanMode.SPOT_AREA,
            [4, 1, 2],
            2,
            {"type": "freeClean", "value": "1,4;1,1;1,2"},
        ),
        (CleanMode.FREE_CLEAN, [5], 1, {"type": "freeClean", "value": "1,5"}),
        (
            CleanMode.CUSTOM_AREA,
            [1580.0, -4087.0, 3833.0, -7525.0],
            1,
            {"type": "customArea", "value": "1580.0,-4087.0,3833.0,-7525.0"},
        ),
    ],
    ids=[
        "single room",
        "two rooms",
        "rooms keep order, passes not in value",
        "free clean mode",
        "custom area unchanged",
    ],
)
async def test_x12_pro_omni_room_cleaning_uses_free_clean(
    class_: str,
    mode: CleanMode,
    area: list[int | float],
    cleanings: int,
    content: dict[str, str],
) -> None:
    info = await hardware.get_static_device_info(class_)
    assert info is not None
    area_command = info.capabilities.clean.action.area
    assert area_command is not None

    command = area_command(mode, area, cleanings)
    assert isinstance(command, CleanAreaV2)
    assert command.NAME == "clean_V2"
    assert command._args == {"act": "start", "content": content}
