from __future__ import annotations

import pytest

from deebot_client import hardware
from deebot_client.capabilities import DeviceType
from deebot_client.commands.json.clean import CleanMower


@pytest.mark.parametrize("class_", ["2i0fns", "0jbd6s"])
async def test_goat_o1200_uses_clean_mower(class_: str) -> None:
    device_info = await hardware.get_static_device_info(class_)
    assert device_info is not None
    capabilities = device_info.capabilities

    assert capabilities.device_type is DeviceType.MOWER
    assert capabilities.clean.action.command is CleanMower
