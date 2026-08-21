from __future__ import annotations

from deebot_client.events import ProtectStateEvent
from deebot_client.hardware import get_static_device_info
from deebot_client.messages import get_message
from deebot_client.messages.json import OnProtectState


async def test_protect_state_capability() -> None:
    device_info = await get_static_device_info("2i0fns")
    assert device_info is not None

    capability = device_info.capabilities.protect_state
    assert capability is not None
    assert capability.event is ProtectStateEvent
    assert capability.get == []
    assert device_info.capabilities.get_refresh_commands(ProtectStateEvent) == []


async def test_protect_state_registration() -> None:
    device_info = await get_static_device_info("2i0fns")
    assert device_info is not None

    assert get_message(OnProtectState.NAME, device_info) is OnProtectState
