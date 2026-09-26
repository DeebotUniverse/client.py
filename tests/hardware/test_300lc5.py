from __future__ import annotations

from deebot_client.capabilities import DeviceType
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import CleanAreaMower, CleanMower, GetCleanInfoV2
from deebot_client.hardware import get_static_device_info


async def test_300lc5_mower_controls() -> None:
    info = await get_static_device_info("300lc5")
    assert info is not None
    capabilities = info.capabilities

    assert capabilities.device_type is DeviceType.MOWER
    assert capabilities.clean.action.command is CleanMower
    assert capabilities.clean.action.area is CleanAreaMower
    assert capabilities.charge.execute is Charge
    assert Charge()._args == {"act": "go"}
    assert capabilities.state.get == [GetChargeState(), GetCleanInfoV2()]
