from __future__ import annotations

from pathlib import Path

from deebot_client import hardware
from deebot_client.capabilities import DeviceType
from deebot_client.commands.json.clean import CleanArea, CleanV2
from deebot_client.const import DataType


async def test_pelc5b_uses_x11_pro_omni_capabilities() -> None:
    """DEEBOT X11 PRO (CN, water hookup) reuses the DEEBOT X11 PRO OMNI (o073ti) definition."""
    folder = Path(hardware.__file__).parent
    assert (folder / "pelc5b.py").resolve() == (folder / "o073ti.py").resolve()
    assert (folder / "pelc5b.py").readlink() == Path("huhcip.py")

    device_info = await hardware.get_static_device_info("pelc5b")
    assert device_info is not None
    assert device_info.data_type is DataType.JSON

    capabilities = device_info.capabilities
    assert capabilities.device_type is DeviceType.VACUUM
    assert capabilities.clean.action.command is CleanV2
    assert capabilities.clean.action.area is CleanArea
    assert capabilities.map is not None
    assert capabilities.station is not None
